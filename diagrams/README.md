# Diagrammes CARIBOOKS

Tous les diagrammes du mémoire (`main.tex`) et de la présentation (`powerpoint.tex`)
sont définis ici en **Mermaid** (`.mmd`) et rendus en **PDF vectoriel** (`.pdf`),
inclus dans les `.tex` via `\includegraphics{diagrams/<nom>.pdf}`.

## Régénérer les PDF

```bash
cd diagrams
./render.sh
```

Prérequis : Node.js (utilise `npx @mermaid-js/mermaid-cli`). La configuration de
rendu est dans `mermaid-config.json` (thème, polices) et `puppeteer-config.json`.

> Si `render.sh` échoue avec `Could not find Chrome (ver. X.Y.Z)` alors que
> cette version est bien installée sous `~/.cache/puppeteer/chrome/...`, la
> résolution automatique du binaire échoue sur cette machine. Contournement :
> `npx puppeteer browsers install chrome@X.Y.Z` (la version exacte est donnée
> dans le message d'erreur), puis ajouter temporairement `"executablePath"`
> dans `puppeteer-config.json` en pointant vers le binaire installé
> (`.../chrome-mac-x64/Google Chrome for Testing.app/Contents/MacOS/Google
> Chrome for Testing`) le temps du rendu — ne pas committer ce chemin, propre
> à chaque machine.

## Inventaire

| Fichier | Type Mermaid | Utilisé dans |
|---|---|---|
| `contexte` | flowchart | main + powerpoint |
| `use_case_isbn` | flowchart (cas d'utilisation) | main |
| `use_case_payment` | flowchart (cas d'utilisation) | main |
| `use_case_global` | flowchart (cas d'utilisation) | main + powerpoint |
| `activites_achat` | flowchart (activités) | main |
| `activites_isbn` | flowchart (activités) | main + powerpoint |
| `sequence_isbn` | sequenceDiagram | main |
| `sequence_paiement` | sequenceDiagram | main + powerpoint |
| `sequence_auth` | sequenceDiagram | main |
| `sequence_admin_commande` | sequenceDiagram | main |
| `classes` | classDiagram | main |
| `objets` | classDiagram (objets) | main |
| `composants` | flowchart | main |
| `mcd` | erDiagram | main |
| `mld` | erDiagram | main + powerpoint |
| `architecture` | flowchart | main + powerpoint |
| `architecture_couches` | flowchart (clean architecture) | powerpoint |
| `deploiement` | flowchart | main + powerpoint |

Les diagrammes sont alignés sur le code réel : entités/colonnes de
`backend/infrastructure/models.py`, endpoints (`/books/isbn-metadata/{isbn}`,
`/orders/paiements/postfinance`, `/auth/token`, `/auth/google`), statuts de
commande (`PENDING`, `PAID`), OpenLibrary comme source unique de métadonnées
ISBN (404 → saisie manuelle, pas de fallback Google Books), et flux
PostFinance (iframe + webhook signé + polling de secours).

> Note : les maquettes UI/UX et les décorations restent en TikZ natif dans les
> `.tex` (pas de type Mermaid équivalent).
