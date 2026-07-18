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
`/orders/paiements/postfinance`, `/auth/token`), statuts de commande
(`PENDING`, `PAID`), fallback OpenLibrary → Google Books, et flux PostFinance
(iframe + webhook signé).

> Note : les maquettes UI/UX et les décorations restent en TikZ natif dans les
> `.tex` (pas de type Mermaid équivalent).
