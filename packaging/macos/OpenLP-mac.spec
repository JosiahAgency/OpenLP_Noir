# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller specification for building OpenLP Noir on macOS.
"""
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


project_root = Path.cwd().resolve()
app_name = "OpenLP Noir"

datas = collect_data_files('openlp', include_py_files=False)
datas.append((str(project_root / 'resources'), 'resources'))
datas.append((str(project_root / 'openlp' / '.version'), 'openlp'))

i18n_build_dir = project_root / 'build' / 'i18n'
if i18n_build_dir.exists():
    datas.append((str(i18n_build_dir), 'resources/i18n'))

hiddenimports = collect_submodules('openlp.plugins')

a = Analysis(
    [str(project_root / 'run_openlp.py')],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=app_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=app_name,
)

app = BUNDLE(
    coll,
    name=f'{app_name}.app',
    icon=None,
    bundle_identifier='org.openlp.noir',
)
