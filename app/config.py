"""Duong dan tai nguyen (chi doc) va du lieu (ghi duoc).

- Chay tu ma nguon: du lieu o ./data trong thu muc code.
- Ban dong goi (.app): du lieu o ~/Library/Application Support/TaskLead.
- Bien TASKLEAD_DATA_DIR de dung thu muc khac (vi du khi chay test).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "Task Lead"
FROZEN = getattr(sys, "frozen", False)

RES_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))

if os.environ.get("TASKLEAD_DATA_DIR"):
    DATA_DIR = Path(os.environ["TASKLEAD_DATA_DIR"])
elif FROZEN:
    DATA_DIR = Path.home() / "Library" / "Application Support" / "TaskLead"
else:
    DATA_DIR = RES_DIR / "data"

DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "tasklead.db"
