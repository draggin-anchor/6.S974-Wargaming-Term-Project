#!/bin/sh
# Render each equation (*.tex except preamble) to a transparent 600-dpi PNG for build.js.
cd "$(dirname "$0")"
for f in *.tex; do
  [ "$f" = preamble.tex ] && continue
  b="${f%.tex}"
  pdflatex -interaction=nonstopmode -halt-on-error "$f" >/dev/null || { echo "failed: $f"; exit 1; }
  magick -density 600 "$b.pdf" -background none -alpha set "$b.png"
  rm -f "$b.aux" "$b.log" "$b.pdf"
done
