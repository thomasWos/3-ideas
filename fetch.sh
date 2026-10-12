#!/usr/bin/env bash
# Download every 3-2-1 newsletter from the WordPress REST API into raw/.
# Resolves paths relative to this script, so it can be run from any directory.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE="https://jamesclear.com/wp-json/wp/v2/3-2-1"
OUT="$HERE/raw"
mkdir -p "$OUT"

total=$(curl -sI "$BASE?per_page=1" | awk '/^x-wp-total:/ {print $2}' | tr -d '\r')
pages=$(( (total + 99) / 100 ))
echo "found $total issues -> $pages pages of 100"

for p in $(seq 1 "$pages"); do
  echo "  fetching page $p/$pages"
  curl -sS "$BASE?per_page=100&page=$p" -o "$OUT/page$p.json"
  sleep 0.4
done

python3 -c "
import json,glob
n=sum(len(json.load(open(f))) for f in glob.glob('$OUT/page*.json'))
print('downloaded', n, 'issues')
"