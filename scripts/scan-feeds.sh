#!/usr/bin/env bash
set -euo pipefail
mkdir -p scan
STAMP=$(date -u +"%Y-%m-%d %H:%M UTC")
{
  echo "# Scan $STAMP"
  echo
  echo "Kilder: DR, TV 2. Breaking = samme sag hos mindst to, eller officiel kilde."
  echo
  for name_url in "DR|https://www.dr.dk/nyheder/service/feeds/allenyheder" "TV2|https://feeds.tv2.dk/nyheder/rss"; do
    name=${name_url%%|*}
    url=${name_url#*|}
    echo "## $name"
    curl -fsSL --max-time 20 "$url" | tr '\n' ' ' | sed 's/<item>/\n<item>/g' | head -n 12 | while read -r item; do
      title=$(printf '%s' "$item" | sed -n 's/.*<title>\(.*\)<\/title>.*/\1/p' | sed 's/<\!\[CDATA\[//;s/\]\]>//;s/^[[:space:]]*//')
      [ -n "$title" ] && echo "- $title"
    done
    echo
  done
} > scan/latest.md
