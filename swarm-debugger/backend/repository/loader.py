import os
import zipfile
import shutil
from typing import Dict, Optional, Tuple


class RepositoryLoader:
    """
    Manages loading target repositories from preset demo-projects or ZIP archives.
    """

    DEMO_ROOT = os.path.abspath(
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "demo-projects")
    )

    @classmethod
    def load_demo(cls, demo_id: str) -> Tuple[str, Dict[str, str]]:
        """
        Loads files from a preset demo project (e.g. bug-01).
        Returns (repo_path, file_contents_dict).
        """
        demo_dir = os.path.join(cls.DEMO_ROOT, demo_id)
        if not os.path.exists(demo_dir):
            # Fallback mock files if directory not yet created
            return demo_dir, {
                "processor.py": (
                    "def slice_batch(items, batch_size):\n"
                    "    batches = []\n"
                    "    for i in range(0, len(items) + 1, batch_size):\n"
                    "        batches.append(items[i:i + batch_size])\n"
                    "    return batches\n"
                ),
                "test_processor.py": (
                    "import pytest\n"
                    "from processor import slice_batch\n\n"
                    "def test_standard_batch():\n"
                    "    assert slice_batch([1, 2, 3, 4], 2) == [[1, 2], [3, 4]]\n\n"
                    "def test_zero_or_negative_batch_size():\n"
                    "    with pytest.raises(ValueError):\n"
                    "        slice_batch([1, 2, 3], batch_size=0)\n"
                )
            }

        files = {}
        for root, _, filenames in os.walk(demo_dir):
            for filename in filenames:
                if filename.endswith(".py") or filename.endswith(".txt") or filename.endswith(".toml"):
                    full_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(full_path, demo_dir).replace("\\", "/")
                    try:
                        with open(full_path, "r", encoding="utf-8") as f:
                            files[rel_path] = f.read()
                    except Exception:
                        pass
        return demo_dir, files

    @classmethod
    def extract_zip(cls, zip_bytes: bytes, target_dir: str) -> Dict[str, str]:
        """Extracts an uploaded zip archive safely into target_dir."""
        os.makedirs(target_dir, exist_ok=True)
        # Stub for zip extraction
        return {}
