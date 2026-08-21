# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller specification for building OpenLP Noir on macOS.
"""
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules
from PySide6.QtCore import QLibraryInfo


project_root = Path.cwd().resolve()
app_name = "OpenLP Noir"
app_icon = project_root / 'packaging' / 'macos' / 'assets' / 'OpenLP-Noir.icns'

qt_prefix = Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.PrefixPath))
qt_webengine_framework = qt_prefix / 'lib' / 'QtWebEngineCore.framework'
qt_helpers_src = qt_webengine_framework / 'Versions' / 'A' / 'Helpers' / 'QtWebEngineProcess.app'

# 'Versions/A' is a symlink alias to the real numbered version (e.g. '6').
# The bundled runtime resolves helper paths through the real version dir,
# not through 'A', so source and destination must both use the real name
# or the app aborts on launch looking for a path that was never created.
qt_webengine_version = (
    (qt_webengine_framework / 'Versions' / 'A').resolve().name
    if (qt_webengine_framework / 'Versions' / 'A').exists()
    else 'A'
)

datas = collect_data_files('openlp', include_py_files=False)
datas.append((str(project_root / 'resources'), 'resources'))
datas.append((str(project_root / 'openlp' / '.version'), 'openlp'))
qt_resources_dir = qt_prefix / 'resources'
if qt_resources_dir.exists():
    for resource_name in (
        'qtwebengine_devtools_resources.pak',
        'qtwebengine_resources.pak',
        'qtwebengine_resources_100p.pak',
        'qtwebengine_resources_200p.pak',
        'v8_context_snapshot.bin',
    ):
        resource_path = qt_resources_dir / resource_name
        if resource_path.exists():
            datas.append((str(resource_path), 'PySide6/Qt6/resources'))
qt_locales_dir = qt_prefix / 'translations' / 'qtwebengine_locales'
if qt_locales_dir.exists():
    datas.append((str(qt_locales_dir), 'PySide6/Qt6/translations/qtwebengine_locales'))

i18n_build_dir = project_root / 'build' / 'i18n'
if i18n_build_dir.exists():
    datas.append((str(i18n_build_dir), 'resources/i18n'))

hiddenimports = collect_submodules('openlp.plugins')

a = Analysis(
    [str(project_root / 'openlp' / '__main__.py')],
    pathex=[str(project_root)],
    binaries=[
        (
            str(qt_helpers_src),
            f'PySide6/Qt6/lib/QtWebEngineCore.framework/Versions/{qt_webengine_version}/Helpers/QtWebEngineProcess.app'
        )
    ] if qt_helpers_src.exists() else [],
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
    icon=str(app_icon) if app_icon.exists() else None,
    bundle_identifier='org.openlp.noir',
)
