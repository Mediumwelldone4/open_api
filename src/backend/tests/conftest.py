import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
BACKEND_SRC = ROOT / "src" / "backend"
if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))
