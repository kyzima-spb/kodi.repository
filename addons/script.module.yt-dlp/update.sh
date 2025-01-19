#!/usr/bin/env sh

set -e

PACKAGE_VERSION="$1"
workdir="${2:-$(pwd)/lib}"

if [ -z "$PACKAGE_VERSION" ]; then
  package="yt_dlp"
else
  package="yt_dlp==${PACKAGE_VERSION}"
fi

python3 -m pip download --no-deps --no-binary :all: -d "$workdir" "$package" \
  && cd "$workdir" \
  && tar --strip-components=1 -xzf ./*.tar.gz \
  && find . -mindepth 1 -maxdepth 1 -not -path "./yt_dlp" -exec rm -rf {} +
