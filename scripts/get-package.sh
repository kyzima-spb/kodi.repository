#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(dirname "$(readlink -f "${0}")")"


log() {
  echo >&2 "$1"
}


usage() {
  echo >&2 "Usage: $(basename "$0") -p PACKAGE_NAME [OPTIONS]"

  if [ "$1" != 'short' ]; then
		cat 1>&2 <<-ENDOFUSAGE

		Updates the version of the addon with an external library to the latest or specified one.

		Options:
		  -p STRING    package name or git repository URL
		  -o STRING    root directory of the addon
		  -v STRING    package version
		  -d STRING    package dependencies

		ENDOFUSAGE
  fi
}


dependencies=()

while getopts "p:o:v:d:" o; do
  case "${o}" in
    p) packageName="${OPTARG}" ;;
    o) addonDir="${OPTARG}" ;;
    v) packageVersion="${OPTARG}" ;;
    d) dependencies+=("${OPTARG}") ;;
    *) usage ;;
  esac
done

test -z "$packageName" && {
  usage 'short'
  echo >&2 'the following arguments are required: -p'
  exit 1
}

test -z "$addonDir" && {
  usage 'short'
  echo >&2 'the following arguments are required: -o'
  exit 1
}

if [[ -z "$packageVersion" ]]; then
  package="$packageName"
else
  package="${packageName}==${packageVersion}"
fi

packageName="$(basename "$packageName" .git)"
addonXml="$addonDir/addon.xml"

log "Install or update an installed package $packageName in the $addonDir directory"
python3 -m pip install -q --no-deps -t "$addonDir/lib" --upgrade "$package" "${dependencies[@]}"

addonId="${addonDir##*/}"
addonName="${addonId##*.}"
packageInfo="$(PYTHONPATH="$addonDir/lib" python3 -m pip show "$packageName")"
version="$(echo "$packageInfo" | sed -n 's/Version: //p')"
author="$(echo "$packageInfo" | sed -nr 's/(Author-email|Author): ([^<]+)( .+)?/\2/p')"

if test -f "$addonXml"
then
  suffix="$(xmlstarlet sel -t -v "/addon/@version" "$addonXml" | grep -oE '[0-9]+$')"
  version="${version}-${suffix}"
  log "Patch version in $addonXml to: $version"
  xmlstarlet ed -L \
      -u "/addon/@id" -v "$addonId" \
      -u "/addon/@name" -v "$addonName" \
      -u "/addon/@version" -v "$version" "$addonXml"
else
  log "Create new addon $addonId"
  cp -r "$SCRIPT_DIR"/addon-template/* "$addonDir"
  xmlstarlet ed -L \
      -a 'addon' -t attr -n 'id' -v "$addonId" \
      -a 'addon' -t attr -n 'name' -v "$addonName" \
      -a 'addon' -t attr -n 'version' -v "${version}-1" \
      -a 'addon' -t attr -n 'provider-name' -v "$author" \
      --var metadata "/addon/extension[@point='xbmc.addon.metadata']" \
      --var assets "/addon/extension[@point='xbmc.addon.metadata']/assets" \
      -i '$assets' -t elem -n 'summary' -v "$(echo "$packageInfo" | sed -n 's/Summary: //p')" \
      -a '$metadata/summary[not(@lang)]' -t attr -n 'lang' -v 'en_GB' \
      -i '$assets' -t elem -n 'description' -v "Packed for KODI: $packageName" \
      -a '$metadata/description[not(@lang)]' -t attr -n 'lang' -v 'en_GB' \
      -i '$assets' -t elem -n 'description' -v "Упаковано для KODI: $packageName" \
      -a '$metadata/description[not(@lang)]' -t attr -n 'lang' -v 'ru_RU' \
      -i '$assets' -t elem -n 'license' -v "$(echo "$packageInfo" | sed -n 's/License: //p')" \
      -i '$assets' -t elem -n 'website' -v "$(echo "$packageInfo" | sed -n 's/Home-page: //p')" \
      -i '$assets' -t elem -n 'source' -v "$(echo "$packageInfo" | sed -n 's/Home-page: //p')" \
      "$addonXml"
fi

if [[ "$addonName" != "$packageName" ]]
then
  log "Rename python package $packageName to $addonName"
  targetPath="$addonDir/lib/${addonName//-/_}"
  [[ ! -d "$targetPath" ]] || rm -r "$targetPath"
  mv "$addonDir/lib/${packageName//-/_}" "$addonDir/lib/${addonName//-/_}"
fi

log "Remove directory dist-info"
rm -rf "$addonDir"/lib/*.dist-info "$addonDir"/lib/tests

exit 0
