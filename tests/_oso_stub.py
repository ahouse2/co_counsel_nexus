import sys
from unittest.mock import MagicMock

def ensure_oso_stub():
    if "oso" not in sys.modules:
        sys.modules["oso"] = MagicMock()
        sys.modules["oso.Oso"] = MagicMock()
