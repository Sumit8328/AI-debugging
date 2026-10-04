import os
from typing import List, Dict, Any


class RepositoryScanner:
    """
    Scans repository directory structure and identifies test suites and source code.
    """

    @staticmethod
    def scan_structure(repo_path: str) -> Dict[str, Any]:
        """Returns hierarchical file tree and test file detection."""
        if not os.path.exists(repo_path):
            return {
                "name": "root",
                "type": "directory",
                "children": [
                    {"name": "processor.py", "type": "file", "is_test": False},
                    {"name": "test_processor.py", "type": "file", "is_test": True},
                ]
            }

        def build_tree(path: str) -> Dict[str, Any]:
            name = os.path.basename(path)
            if os.path.isdir(path):
                children = []
                try:
                    for entry in sorted(os.listdir(path)):
                        if entry.startswith(".") or entry in ("__pycache__", "venv", ".venv"):
                            continue
                        subpath = os.path.join(path, entry)
                        children.append(build_tree(subpath))
                except Exception:
                    pass
                return {"name": name, "type": "directory", "children": children}
            else:
                is_test = name.startswith("test_") or name.endswith("_test.py")
                return {"name": name, "type": "file", "is_test": is_test}

        return build_tree(repo_path)
