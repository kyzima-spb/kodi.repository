#!/usr/bin/env sh

set -e

PACKAGE_NAME="yt_dlp"
PACKAGE_VERSION="$1"
workdir="${2:-$(pwd)/lib}"

SCRIPT_PATH="$(readlink -f "$0")"
SCRIPT_DIR="$(dirname "$SCRIPT_PATH")"

if [ -z "$PACKAGE_VERSION" ]; then
  package="$PACKAGE_NAME"
else
  package="${PACKAGE_NAME}==${PACKAGE_VERSION}"
fi

python3 -m pip install hatchling \
  && cd "$workdir" \
  && python3 -m pip download --no-binary :all: --no-deps --no-build-isolation "$package" \
  && tar --strip-components=1 -xzf ./*.tar.gz \
  && xmlstarlet ed -L -u "/addon/@version" -v "$(sed -nr 's/^Version: (.*)$/\1/p' PKG-INFO)" "$SCRIPT_DIR/addon.xml" \
  && find . -mindepth 1 -maxdepth 1 -not -path "./yt_dlp" -exec rm -rf {} +
