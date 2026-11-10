import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
TOOLS_DIR = Path(__file__).resolve().parents[1]

for p in (REPO_ROOT, TOOLS_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
