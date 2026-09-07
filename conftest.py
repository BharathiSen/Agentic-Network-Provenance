# conftest.py
import sys
from pathlib import Path

ROOT = Path(__file__).parent
for svc in (ROOT / "services").iterdir():
    src = svc / "src"
    if src.is_dir():
        sys.path.insert(0, str(src))