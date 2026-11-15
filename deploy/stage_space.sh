#!/usr/bin/env bash
# Stage the free static Hugging Face Space: the web app built in browser mode (the model runs in
# the visitor's browser), the sample invoices and the Space card.
#   deploy/stage_space.sh            -> build/space
set -euo pipefail
cd "$(dirname "$0")/.."
out=build/space
rm -rf "$out" && mkdir -p "$out"
(cd web && VITE_READER=browser npx vite build --outDir "../$out" --emptyOutDir)
mkdir -p "$out/samples" && cp app/samples/*.jpg "$out/samples/"
cp deploy/huggingface-static/README.md "$out/README.md"
du -sh "$out"
