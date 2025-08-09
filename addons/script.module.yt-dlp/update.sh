#!/usr/bin/env sh

set -e

PACKAGE_NAME="yt_dlp"
PACKAGE_VERSION="$1"

SCRIPT_PATH="$(readlink -f "$0")"
SCRIPT_DIR="$(dirname "$SCRIPT_PATH")"

if [ -z "$PACKAGE_VERSION" ]; then
  package="$PACKAGE_NAME"
else
  package="${PACKAGE_NAME}==${PACKAGE_VERSION}"
fi

python3 -m pip install -t "${SCRIPT_DIR}/lib" --upgrade "$package" && \
  version="$(PYTHONPATH="${SCRIPT_DIR}/lib" python3 -m pip show "$package" | awk '/^Version:/{print $2}')" && \
  suffix="$(xmlstarlet sel -t -v "/addon/@version" "${SCRIPT_DIR}/addon.xml" | awk -F- '{print $2}')" && \
  [ -n "$suffix" ] && version="${version}-$suffix" || true && \
  xmlstarlet ed -L -u "/addon/@version" -v "$version" "${SCRIPT_DIR}/addon.xml" && \
  cd "${SCRIPT_DIR}/lib" && \
  find . -mindepth 1 -maxdepth 1 -not -path "./yt_dlp" -not -path "./yt_dlp_utils" -exec rm -rf {} +
