#!/bin/bash
# Task Lead — nhap doi de chay. Lan dau se tu cai moi truong (khoang 1 phut).
set -e
cd "$(dirname "$0")"

# Uu tien Python 3.12 di kem bo cong cu cua NXM DZS1TG, khong co thi dung python3 cua may.
PY="/Users/admin/Desktop/nxm-dzs1tg/.toolchain/python/bin/python3"
[ -x "$PY" ] || PY="$(command -v python3 || true)"
if [ -z "$PY" ]; then
  echo "  [!] Chua co python3. Cai tai python.org hoac chay: xcode-select --install"
  read -n 1 -s -r -p "Nhan phim bat ky de dong..."
  exit 1
fi

if [ ! -d ".venv" ]; then
  echo "  Dang tao moi truong ao (.venv)..."
  "$PY" -m venv .venv
fi
if [ ! -f ".venv/.deps_ok" ]; then
  echo "  Dang cai thu vien..."
  .venv/bin/python -m pip install --upgrade pip >/dev/null
  .venv/bin/python -m pip install -r requirements.txt
  touch ".venv/.deps_ok"
fi

echo "  Dang mo Task Lead... (dong cua so Terminal nay de tat app)"
.venv/bin/python desktop.py
