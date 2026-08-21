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

echo "==> Packaging ${APP_NAME} ${VERSION} for macOS"

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
echo "App bundle: ${APP_PATH}"

if [[ ${SKIP_DMG} -eq 1 ]]; then
  echo "Skipping DMG creation (--skip-dmg)."
  exit 0
fi

if ! command -v hdiutil >/dev/null 2>&1; then
  echo "hdiutil is not available, cannot create DMG." >&2
  exit 1
fi

OUTPUT_DIR="${ROOT_DIR}/dist/installer/mac"
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
