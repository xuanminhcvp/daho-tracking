# -*- mode: python ; coding: utf-8 -*-
# Spec dong goi Task Lead (macOS Apple Silicon). Chay boi build_app.command:
#   python -m PyInstaller --noconfirm --clean "Task Lead.spec"
# Tai nguyen CHI-DOC di kem .app; du lieu ghi duoc nam o ~/Library/Application Support/TaskLead (xem app/config.py).
import os
import re

from PyInstaller.utils.hooks import collect_submodules

ROOT = os.path.abspath(os.getcwd())

datas = [
    ('app/templates', 'app/templates'),
    ('app/static', 'app/static'),
]
hiddenimports = ['WebKit', 'Foundation', 'AppKit', 'encodings.idna']
hiddenimports += collect_submodules('app')
hiddenimports += collect_submodules('webview')
hiddenimports += collect_submodules('cryptography')

a = Analysis(
    ['desktop.py'],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'pytest'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Task Lead',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch='arm64',
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, upx_exclude=[], name='Task Lead')

_VER = re.search(r'VERSION = "([^"]+)"', open(os.path.join(ROOT, 'app', 'version.py'), encoding='utf-8').read()).group(1)

app = BUNDLE(
    coll,
    name='Task Lead.app',
    icon=os.path.join(ROOT, 'assets', 'TaskLead.icns'),
    bundle_identifier='vn.tasklead.app',
    info_plist={
        'CFBundleName': 'Task Lead',
        'CFBundleDisplayName': 'Task Lead',
        'CFBundleShortVersionString': _VER,
        'CFBundleVersion': os.environ.get('TASKLEAD_BUILD_STAMP', 'dev'),
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '11.0',
    },
)
