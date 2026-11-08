#!/usr/bin/env bash
# <dir>/slides.html を PDF に印刷し、<dir>/slides/ へページごとの PNG に書き出す。
# 要るもの: chromium、pdftoppm（poppler）、Noto Sans CJK JP
set -euo pipefail

if [ $# -ne 1 ] || [ ! -f "$1/slides.html" ]; then
  echo "Usage: $0 <dir containing slides.html>" >&2
  exit 1
fi

cd "$1"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

chromium --headless --no-pdf-header-footer \
  --print-to-pdf="$tmp/slides.pdf" "file://$PWD/slides.html" 2>/dev/null

rm -rf slides
mkdir slides
pdftoppm -png -scale-to-x 1600 -scale-to-y -1 "$tmp/slides.pdf" slides/
# pdftoppm はページ数で桁を決めるので、01.png の形にそろえる
for f in slides/-*.png; do
  n=${f#slides/-}
  mv "$f" "slides/$(printf '%02d' "$((10#${n%.png}))").png"
done

echo "Wrote $(ls slides | wc -l) slides to $1/slides/"
