"""Stage a complete JSON export before touching the publishable data tree.

Git commit / Pages artifact is the publication transaction. Individual local
file renames are atomic; the deployment must only run after this completes.
"""

import os
import tempfile
from pathlib import Path

from services.writer import Writer


def publish_json(files, root="data"):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".export-", dir=root) as directory:
        staging = Path(directory)
        for name, value in files.items():
            Writer.write_json(value, staging / name)
        # No public file is touched unless every file serializes successfully.
        for name in files:
            destination = root / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            os.replace(staging / name, destination)
