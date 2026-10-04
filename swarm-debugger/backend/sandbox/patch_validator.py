import os
import re
from typing import Tuple, List, Dict, Optional

MAX_PATCH_BYTES = 100 * 1024  # 100 KB
MAX_PATCH_LINES = 1000

DANGEROUS_PATTERNS = [
    r"import\s+subprocess",
    r"subprocess\.",
    r"os\.system",
    r"os\.popen",
    r"shutil\.rmtree",
    r"__import__\s*\(",
    r"eval\s*\(",
    r"exec\s*\(",
    r"socket\.",
    r"requests\.",
    r"urllib\.",
    r"webbrowser\.",
    r"pty\.",
    r"compile\s*\(",
]

SECRET_PATTERNS = [
    r"\.env",
    r"id_rsa",
    r"id_ed25519",
    r"/etc/passwd",
    r"/etc/shadow",
    r"OPENAI_API_KEY",
    r"AWS_SECRET",
    r"BEGIN\s+PRIVATE\s+KEY",
]

PATH_TRAVERSAL_PATTERNS = [
    r"\.\.[/\\]",
    r"[/\\]\.\.",
]

ABSOLUTE_PATH_PATTERNS = [
    r"^/etc[/\\]",
    r"^/var[/\\]",
    r"^/usr[/\\]",
    r"^/root[/\\]",
    r"^/home[/\\]",
    r"^/tmp[/\\]",
    r"^[a-zA-Z]:[/\\]",
    r"^~[/\\]",
]


class PatchSafetyValidator:
    """
    Validates candidate patches before any sandbox application.
    Enforces isolated code execution rules:
    - No execution directly on the host
    - No dangerous system, network, or process access
    - No path traversal or access to secrets / host files
    - Strict unified diff structure validation and in-workspace application
    """

    @classmethod
    def validate_patch(cls, patch_diff: str) -> Tuple[bool, str]:
        """
        Performs static analysis and safety checks on a proposed patch diff.
        Returns (is_safe, error_message).
        """
        if not patch_diff or not patch_diff.strip():
            return False, "Patch diff is empty"

        # Check patch size
        raw_bytes = patch_diff.encode("utf-8")
        if len(raw_bytes) > MAX_PATCH_BYTES:
            return False, f"Patch size ({len(raw_bytes)} bytes) exceeds maximum limit of {MAX_PATCH_BYTES} bytes"

        lines = patch_diff.splitlines()
        if len(lines) > MAX_PATCH_LINES:
            return False, f"Patch line count ({len(lines)}) exceeds maximum limit of {MAX_PATCH_LINES} lines"

        # Check for path traversal in patch
        for pattern in PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, patch_diff):
                return False, f"Path traversal attempt detected in patch: {pattern}"

        # Check for secret access
        for pattern in SECRET_PATTERNS:
            if re.search(pattern, patch_diff, re.IGNORECASE):
                return False, f"Patch contains reference to protected credential or file pattern: {pattern}"

        # Check for dangerous system or network execution patterns
        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, patch_diff, re.IGNORECASE):
                return False, f"Patch contains restricted pattern violating sandbox security policy: {pattern}"

        # Validate target file paths in patch headers
        target_files = cls.extract_target_files(patch_diff)
        for target in target_files:
            # Check absolute path
            for pattern in ABSOLUTE_PATH_PATTERNS:
                if re.search(pattern, target):
                    return False, f"Patch attempts to target absolute or forbidden system path: {target}"
            if ".." in target or target.startswith("/") or target.startswith("\\"):
                return False, f"Patch target file attempts path escape: {target}"

        # Ensure patch looks like a valid diff or code replacement
        has_diff_headers = any(line.startswith("---") or line.startswith("+++") or line.startswith("@@") for line in lines)
        has_code_markers = any("def " in line or "return " in line or "class " in line for line in lines)
        if not (has_diff_headers or has_code_markers):
            return False, "Patch does not appear to contain valid unified diff or Python code modifications"

        return True, "Patch passed safety and formatting checks"

    @classmethod
    def extract_target_files(cls, patch_diff: str) -> List[str]:
        """
        Extracts modified relative file paths from unified diff headers.
        """
        files = []
        for line in patch_diff.splitlines():
            line_clean = line.strip()
            # Match +++ b/filename.py or +++ filename.py
            if line_clean.startswith("+++"):
                raw_path = line_clean[3:].strip()
                # Remove b/ prefix if present
                if raw_path.startswith("b/"):
                    raw_path = raw_path[2:]
                elif raw_path.startswith("b\\"):
                    raw_path = raw_path[2:]
                # Strip timestamps if present (e.g. +++ file.py\t2026-...)
                raw_path = raw_path.split("\t")[0].strip()
                if raw_path and raw_path != "/dev/null" and raw_path not in files:
                    files.append(raw_path.replace("\\", "/"))
            elif line_clean.startswith("---") and not files:
                raw_path = line_clean[3:].strip()
                if raw_path.startswith("a/"):
                    raw_path = raw_path[2:]
                elif raw_path.startswith("a\\"):
                    raw_path = raw_path[2:]
                raw_path = raw_path.split("\t")[0].strip()
                if raw_path and raw_path != "/dev/null" and raw_path not in files:
                    files.append(raw_path.replace("\\", "/"))
        return files

    @classmethod
    def apply_patch(cls, workspace_path: str, patch_diff: str) -> Tuple[bool, str]:
        """
        Applies unified diff hunks safely into the target workspace files.
        Only modifies files inside workspace_path.
        """
        is_safe, err = cls.validate_patch(patch_diff)
        if not is_safe:
            return False, err

        target_files = cls.extract_target_files(patch_diff)
        if not target_files:
            # Fallback: check if single Python file exists in workspace
            py_files = [f for f in os.listdir(workspace_path) if f.endswith(".py") and not f.startswith("test_")]
            if len(py_files) == 1:
                target_files = [py_files[0]]
            else:
                return False, "Could not determine target source file from patch headers"

        # Split patch into per-file diff blocks
        file_diff_map = cls._split_patch_by_file(patch_diff, target_files)

        for rel_file, file_patch in file_diff_map.items():
            full_file_path = os.path.abspath(os.path.join(workspace_path, rel_file))
            # Security verification: path must resolve inside workspace
            abs_workspace = os.path.abspath(workspace_path)
            if not full_file_path.startswith(abs_workspace):
                return False, f"Target file '{rel_file}' resolves outside the temporary workspace"

            if not os.path.isfile(full_file_path):
                return False, f"Target file '{rel_file}' does not exist in workspace"

            try:
                with open(full_file_path, "r", encoding="utf-8") as f:
                    original_content = f.read()
            except Exception as e:
                return False, f"Failed to read '{rel_file}': {str(e)}"

            applied_content, apply_err = cls._apply_hunks_to_content(original_content, file_patch)
            if apply_err:
                return False, f"Failed applying patch to '{rel_file}': {apply_err}"

            try:
                with open(full_file_path, "w", encoding="utf-8") as f:
                    f.write(applied_content)
            except Exception as e:
                return False, f"Failed to write modified '{rel_file}': {str(e)}"

        return True, "Patch applied successfully"

    @classmethod
    def _split_patch_by_file(cls, patch_diff: str, target_files: List[str]) -> Dict[str, str]:
        """Splits multi-file patches into individual file diff contents."""
        if len(target_files) <= 1:
            rel_file = target_files[0] if target_files else "processor.py"
            return {rel_file: patch_diff}

        result = {}
        lines = patch_diff.splitlines()
        current_file = None
        current_lines = []

        for line in lines:
            if line.startswith("--- "):
                if current_file and current_lines:
                    result[current_file] = "\n".join(current_lines)
                    current_lines = []
                # detect next file
                matched = False
                for tf in target_files:
                    if tf in line:
                        current_file = tf
                        matched = True
                        break
                if not matched:
                    current_file = target_files[0]
            current_lines.append(line)

        if current_file and current_lines:
            result[current_file] = "\n".join(current_lines)

        return result or {target_files[0]: patch_diff}

    @classmethod
    def _apply_hunks_to_content(cls, content: str, patch_str: str) -> Tuple[str, Optional[str]]:
        """
        Parses unified diff hunks and applies them to original string content.
        """
        lines = content.splitlines(keepends=True)
        # Normalize newlines
        lines_clean = [l.rstrip("\r\n") for l in lines]

        # Parse hunks from patch_str
        patch_lines = patch_str.splitlines()
        hunks = []
        current_hunk = None

        for pline in patch_lines:
            if pline.startswith("@@"):
                if current_hunk:
                    hunks.append(current_hunk)
                current_hunk = {"header": pline, "lines": []}
            elif current_hunk is not None:
                current_hunk["lines"].append(pline)

        if current_hunk:
            hunks.append(current_hunk)

        if not hunks:
            # If no @@ markers, look for lines starting with - and +
            minus_lines = [l[1:].strip() for l in patch_lines if l.startswith("-") and not l.startswith("---")]
            plus_lines = [l[1:].strip() for l in patch_lines if l.startswith("+") and not l.startswith("+++")]
            if minus_lines:
                # Try simple string replacement of minus lines with plus lines
                content_mod = content
                for minus in minus_lines:
                    for plus in plus_lines:
                        if minus in content_mod:
                            content_mod = content_mod.replace(minus, plus, 1)
                            return content_mod, None
            return content, "No valid unified diff hunks found in patch"

        # Apply hunks
        current_lines = list(lines_clean)

        for hunk in hunks:
            hunk_lines = hunk["lines"]
            old_hunk_lines = []
            new_hunk_lines = []

            for hl in hunk_lines:
                if hl.startswith("-"):
                    old_hunk_lines.append(hl[1:])
                elif hl.startswith("+"):
                    new_hunk_lines.append(hl[1:])
                elif hl.startswith(" "):
                    old_hunk_lines.append(hl[1:])
                    new_hunk_lines.append(hl[1:])
                elif hl.startswith("\\"):
                    continue
                else:
                    # treat as context line
                    old_hunk_lines.append(hl)
                    new_hunk_lines.append(hl)

            # Match old_hunk_lines in current_lines
            match_idx = cls._find_hunk_location(current_lines, old_hunk_lines)
            if match_idx is None:
                # Try stripped context search
                match_idx = cls._find_hunk_location_fuzzy(current_lines, old_hunk_lines)

            if match_idx is None:
                return content, f"Hunk context could not be matched: '{hunk['header']}'"

            # Replace slice
            current_lines = (
                current_lines[:match_idx] +
                new_hunk_lines +
                current_lines[match_idx + len(old_hunk_lines):]
            )

        newline_char = "\n"
        return newline_char.join(current_lines) + newline_char, None

    @staticmethod
    def _find_hunk_location(file_lines: List[str], hunk_old: List[str]) -> Optional[int]:
        """Finds exact slice match for old hunk lines in file."""
        if not hunk_old:
            return 0
        hunk_len = len(hunk_old)
        for i in range(len(file_lines) - hunk_len + 1):
            if file_lines[i:i + hunk_len] == hunk_old:
                return i
        return None

    @staticmethod
    def _find_hunk_location_fuzzy(file_lines: List[str], hunk_old: List[str]) -> Optional[int]:
        """Finds fuzzy match ignoring leading/trailing whitespace."""
        if not hunk_old:
            return 0
        hunk_clean = [l.strip() for l in hunk_old]
        hunk_len = len(hunk_clean)
        for i in range(len(file_lines) - hunk_len + 1):
            window = [l.strip() for l in file_lines[i:i + hunk_len]]
            if window == hunk_clean:
                return i
        return None
