#!/bin/bash
# Build Task Lead cho Mac (Apple Silicon): .app + .dmg (co loi tat Applications). Nhap doi hoac chay trong Terminal.
# Ket qua: dist/Task Lead.app va ban-build/TaskLead-v<phien ban>-<ngay gio>.dmg
set -e
cd "$(dirname "$0")"
APPNAME="Task Lead"
APP="dist/$APPNAME.app"

step() { echo; echo "==> $*"; }
fail() { echo; echo "  [LOI] $*"; read -n 1 -s -r -p "Nhan phim bat ky de dong..." || true; exit 1; }

[ -x .venv/bin/python ] || fail "Chua co .venv — chay run.command mot lan truoc"
PY=.venv/bin/python
VER=$("$PY" -c 'from app.version import VERSION; print(VERSION)')
STAMP=$(date +%Y%m%d-%H%M)
export TASKLEAD_BUILD_STAMP="$STAMP"

step "1/5 Thu vien build"
"$PY" -m pip install -q -r requirements.txt pyinstaller || fail "pip install"

step "2/5 Chay test"
"$PY" -m pip install -q pytest || fail "pip pytest"
"$PY" -m pytest -q || fail "Test khong qua — khong build"

step "3/5 Icon (.icns)"
[ -f assets/icon-1024.png ] || "$PY" tools/make_icon.py || fail "tao icon"
rm -rf assets/TaskLead.iconset && mkdir -p assets/TaskLead.iconset
for s in 16 32 128 256 512; do
  sips -z $s $s assets/icon-1024.png --out "assets/TaskLead.iconset/icon_${s}x${s}.png" >/dev/null || fail "sips $s"
  sips -z $((s*2)) $((s*2)) assets/icon-1024.png --out "assets/TaskLead.iconset/icon_${s}x${s}@2x.png" >/dev/null || fail "sips @2x $s"
done
iconutil -c icns assets/TaskLead.iconset -o assets/TaskLead.icns || fail "iconutil"
rm -rf assets/TaskLead.iconset

step "4/5 PyInstaller + ky ad-hoc"
"$PY" -m PyInstaller --noconfirm --clean "Task Lead.spec" || fail "PyInstaller"
xattr -cr "$APP" 2>/dev/null || true
codesign --force --deep -s - "$APP" || fail "codesign"
codesign --verify --deep --strict "$APP" && echo "  ky OK"

step "5/5 DMG"
mkdir -p ban-build
DMG="ban-build/TaskLead-v${VER}-${STAMP}.dmg"
rm -rf dmg_stage "$DMG"
mkdir -p dmg_stage
cp -R "$APP" dmg_stage/
ln -s /Applications dmg_stage/Applications
cat > dmg_stage/HUONG-DAN-MO-APP.txt <<'TXT'
1. Keo "Task Lead" vao thu muc Applications.
2. Lan dau mo: chuot phai vao app > Open > Open (app chua ky boi Apple nen macOS hoi lai).
   Neu van bi chan, mo Terminal chay:  xattr -dr com.apple.quarantine "/Applications/Task Lead.app"
Du lieu nam o ~/Library/Application Support/TaskLead (xoa app khong mat du lieu).
TXT
hdiutil create -volname "$APPNAME" -srcfolder dmg_stage -ov -format UDZO "$DMG" -quiet || fail "hdiutil"
rm -rf dmg_stage

echo
echo "  XONG:"
echo "    $APP"
echo "    $DMG ($(du -h "$DMG" | cut -f1))"
