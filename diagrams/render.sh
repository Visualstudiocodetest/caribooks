#!/usr/bin/env bash
# Régénère tous les diagrammes (.mmd -> .pdf) avec mermaid-cli.
# Usage : ./render.sh   (depuis le dossier diagrams/)
set -euo pipefail
cd "$(dirname "$0")"

for f in *.mmd; do
  name="${f%.mmd}"
  echo "→ $name"
  npx -y @mermaid-js/mermaid-cli@latest \
    -i "$f" -o "$name.pdf" \
    -c mermaid-config.json -p puppeteer-config.json --pdfFit
done
echo "Terminé : $(ls -1 *.pdf | wc -l | tr -d ' ') diagrammes générés."
