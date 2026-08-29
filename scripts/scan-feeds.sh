#!/usr/bin/env bash
set -uo pipefail
mkdir -p scan
STAMP=$(date -u +"%Y-%m-%d %H:%M UTC")
OUT=scan/latest.md
{
  echo "# Scan $STAMP"
  echo
  echo "Kilder forsøgt: DR, TV 2, Berlingske. En død kilde stopper ikke scannet."
  echo
} > "$OUT"

fetch() {
  local name="$1" url="$2"
  echo "## $name" >> "$OUT"
  if ! html=$(curl -fsSL --max-time 20 -A "MorgentidendeScan/1.0" "$url" 2>/dev/null); then
    echo "- (feed ikke nået)" >> "$OUT"
    echo >> "$OUT"
    return 0
  fi
  printf '%s' "$html" | tr '\n' ' ' | sed 's/<item>/\n<item>/g' | sed 's/<entry>/\n<entry>/g' | head -n 16 | while read -r item; do
    title=$(printf '%s' "$item" | sed -n 's/.*<title[^>]*>\(.*\)<\/title>.*/\1/p' | sed 's/<\!\[CDATA\[//;s/\]\]>//;s/<[^>]*>//g;s/^[[:space:]]*//;s/[[:space:]]*$//')
    [ -n "$title" ] && [ "$title" != "$name" ] && echo "- $title" >> "$OUT"
  done
  echo >> "$OUT"
}

fetch "DR" "https://www.dr.dk/nyheder/service/feeds/allenyheder"
fetch "TV2" "https://www.tv2.dk/rss"
fetch "Berlingske" "https://www.berlingske.dk/rss"
