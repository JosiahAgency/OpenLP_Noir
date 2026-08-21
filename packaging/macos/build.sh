#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${ROOT_DIR}"

CLEAN=0
SKIP_DMG=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --clean)
      CLEAN=1
      ;;
    --skip-dmg)
      SKIP_DMG=1
      ;;
    *)
      echo "Unknown option: $1" >&2
      echo "Usage: packaging/macos/build.sh [--clean] [--skip-dmg]" >&2
      exit 2
      ;;
  esac
  shift
done

VENV_BIN="${ROOT_DIR}/venv/bin"
PYINSTALLER_BIN="${VENV_BIN}/pyinstaller"
LRELEASE_BIN="${VENV_BIN}/pyside6-lrelease"
MACDEPLOYQT_BIN="${VENV_BIN}/pyside6-macdeployqt"

if [[ ! -x "${PYINSTALLER_BIN}" ]]; then
  echo "Missing ${PYINSTALLER_BIN}. Install build dependencies in venv first." >&2
  exit 1
fi
if [[ ! -x "${LRELEASE_BIN}" ]]; then
  echo "Missing ${LRELEASE_BIN}. Install PySide6 in venv first." >&2
  exit 1
fi
VERSION_FILE="${ROOT_DIR}/openlp/.version"
if [[ ! -f "${VERSION_FILE}" ]]; then
  echo "Missing version file: ${VERSION_FILE}" >&2
  exit 1
fi
VERSION="$(head -n 1 "${VERSION_FILE}" | tr -d '\r\n')"
APP_NAME="OpenLP Noir"
ASSETS_DIR="${ROOT_DIR}/packaging/macos/assets"
ICONSET_DIR="${ROOT_DIR}/build/macos-iconset/OpenLP-Noir.iconset"
ICNS_PATH="${ASSETS_DIR}/OpenLP-Noir.icns"

echo "==> Packaging ${APP_NAME} ${VERSION} for macOS"

mkdir -p "${ASSETS_DIR}"
if command -v iconutil >/dev/null 2>&1; then
  echo "==> Building app icon (.icns)"
  rm -rf "${ICONSET_DIR}"
  mkdir -p "${ICONSET_DIR}"
  cp "${ROOT_DIR}/resources/images/openlp-logo-16x16.png" "${ICONSET_DIR}/icon_16x16.png"
  cp "${ROOT_DIR}/resources/images/openlp-logo-32x32.png" "${ICONSET_DIR}/icon_16x16@2x.png"
  cp "${ROOT_DIR}/resources/images/openlp-logo-32x32.png" "${ICONSET_DIR}/icon_32x32.png"
  cp "${ROOT_DIR}/resources/images/openlp-logo-64x64.png" "${ICONSET_DIR}/icon_32x32@2x.png"
  cp "${ROOT_DIR}/resources/images/openlp-logo-128x128.png" "${ICONSET_DIR}/icon_128x128.png"
  cp "${ROOT_DIR}/resources/images/openlp-logo-256x256.png" "${ICONSET_DIR}/icon_128x128@2x.png"
  cp "${ROOT_DIR}/resources/images/openlp-logo-256x256.png" "${ICONSET_DIR}/icon_256x256.png"
  sips -z 512 512 "${ROOT_DIR}/resources/images/openlp-logo-256x256.png" --out "${ICONSET_DIR}/icon_256x256@2x.png" >/dev/null
  cp "${ICONSET_DIR}/icon_256x256@2x.png" "${ICONSET_DIR}/icon_512x512.png"
  cp "${ICONSET_DIR}/icon_256x256@2x.png" "${ICONSET_DIR}/icon_512x512@2x.png"
  iconutil -c icns "${ICONSET_DIR}" -o "${ICNS_PATH}"
fi

I18N_SRC="${ROOT_DIR}/resources/i18n"
I18N_OUT="${ROOT_DIR}/build/i18n"
mkdir -p "${I18N_OUT}"
echo "==> Compiling translations"
while IFS= read -r -d '' TS_FILE; do
  QM_FILE="${I18N_OUT}/$(basename "${TS_FILE%.ts}.qm")"
  "${LRELEASE_BIN}" "${TS_FILE}" -qm "${QM_FILE}" -silent
done < <(find "${I18N_SRC}" -name '*.ts' -print0)

PYI_ARGS=(--noconfirm "${ROOT_DIR}/packaging/macos/OpenLP-mac.spec")
if [[ ${CLEAN} -eq 1 ]]; then
  PYI_ARGS=(--clean "${PYI_ARGS[@]}")
fi

echo "==> Building app bundle with PyInstaller"
"${PYINSTALLER_BIN}" "${PYI_ARGS[@]}"

APP_PATH="${ROOT_DIR}/dist/${APP_NAME}.app"
if [[ ! -d "${APP_PATH}" ]]; then
  echo "Build completed but app bundle not found: ${APP_PATH}" >&2
  exit 1
fi
if [[ -x "${MACDEPLOYQT_BIN}" ]]; then
  echo "==> Running macdeployqt to fix Qt framework/helper layout"
  "${MACDEPLOYQT_BIN}" "${APP_PATH}" -always-overwrite -verbose=2
else
  echo "==> pyside6-macdeployqt not available in this PySide6 build; skipping macdeployqt step"
fi

WEBENGINE_HELPER="${APP_PATH}/Contents/Frameworks/PySide6/Qt6/lib/QtWebEngineCore.framework/Versions/A/Helpers/QtWebEngineProcess.app/Contents/MacOS/QtWebEngineProcess"
if [[ ! -x "${WEBENGINE_HELPER}" ]]; then
  echo "QtWebEngineProcess helper is still missing after macdeployqt: ${WEBENGINE_HELPER}" >&2
  exit 1
fi
echo "App bundle: ${APP_PATH}"

OUTPUT_DIR="${ROOT_DIR}/dist/installer/mac"
mkdir -p "${OUTPUT_DIR}"
ZIP_PATH="${OUTPUT_DIR}/OpenLP-Noir-${VERSION}-macOS.zip"
echo "==> Creating ZIP app package"
rm -f "${ZIP_PATH}"
ditto -c -k --sequesterRsrc --keepParent "${APP_PATH}" "${ZIP_PATH}"
echo "Installer ZIP: ${ZIP_PATH}"

if [[ ${SKIP_DMG} -eq 1 ]]; then
  echo "Skipping DMG creation (--skip-dmg)."
  exit 0
fi

if ! command -v hdiutil >/dev/null 2>&1; then
  echo "hdiutil is not available, cannot create DMG." >&2
  exit 1
fi

STAGING_DIR="${ROOT_DIR}/build/macos-dmg-staging"
DMG_PATH="${OUTPUT_DIR}/OpenLP-Noir-${VERSION}-macOS.dmg"

echo "==> Creating DMG"
rm -rf "${STAGING_DIR}"
mkdir -p "${OUTPUT_DIR}" "${STAGING_DIR}"
cp -R "${APP_PATH}" "${STAGING_DIR}/"
ln -s /Applications "${STAGING_DIR}/Applications"

hdiutil create \
  -volname "OpenLP Noir" \
  -srcfolder "${STAGING_DIR}" \
  -ov \
  -format UDZO \
  "${DMG_PATH}"
rm -rf "${STAGING_DIR}"

echo "Installer DMG: ${DMG_PATH}"
