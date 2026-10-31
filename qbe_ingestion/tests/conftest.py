# -*- coding: utf-8 -*-
import sys
from pathlib import Path

ECOSYSTEM_ROOT = Path(__file__).resolve().parents[2]
if str(ECOSYSTEM_ROOT) not in sys.path:
    sys.path.insert(0, str(ECOSYSTEM_ROOT))
