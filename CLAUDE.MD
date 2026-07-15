# AGENTS.md - Directives pour l'IA et les Développeurs (Projet caribooks)

Ce document définit les règles de développement, l'architecture et les principes de conception pour le projet **caribooks**. Toutes les suggestions de code et les refactorisations doivent respecter ces directives.

## 1. Principes Fondamentaux de Conception

### 1.1 KISS (Keep It Simple, Stupid) [web:17][web:26]
- **Simplicité avant tout :** Ne sur-ingéniérisez pas. Privilégiez des solutions directes et lisibles.
- **YAGNI (You Aren't Gonna Need It) :** N'implémentez pas de fonctionnalités ou d'abstractions (comme des interfaces complexes) en prévision d'un besoin futur hypothétique [web:18].
- **Code concis :** Si une méthode ou un composant peut être écrit en moins de lignes tout en restant clair, faites-le. La lisibilité prime sur la concision extrême [web:20].

### 1.2 SOLID [web:21][web:28]
- **S (Single Responsibility) :** Une classe, une fonction ou un composant React ne doit avoir qu'une seule raison de changer.
- **O (Open/Closed) :** Les entités doivent être ouvertes à l'extension mais fermées à la modification. Utilisez la composition en React et l'injection de dépendances en FastAPI.
- **L (Liskov Substitution) :** Les sous-types doivent pouvoir remplacer leurs types de base sans altérer le comportement (important pour les modèles Pydantic).
- **I (Interface Segregation) :** Créez des interfaces spécifiques plutôt que des interfaces monolithiques (ex: types TypeScript précis pour Next.js).
- **D (Dependency Inversion) :** Dépendez d'abstractions, pas de classes concrètes. En FastAPI, utilisez le système de `Depends()` pour l'injection [web:37].

### 1.3 KKS (Adapté pour le Naming & Structuration) [web:9]
Bien que le KKS soit originellement utilisé dans l'industrie, nous appliquons sa philosophie d'identification structurée :
- **Standardisation :** Les noms de fichiers, variables, et endpoints doivent suivre une nomenclature stricte et hiérarchique (ex: `api/v1/books/{isbn}`).
- **Traçabilité :** Les logs côté backend doivent identifier clairement le module, la fonction et l'état de l'erreur.

## 2. Stack Technique et Directives Spécifiques

### 2.1 Backend : FastAPI (Python) [web:37]
- **Base de données :** Utilisez exclusivement **mySQL** comme moteur de base de données (pas de SQLite/PostgreSQL).
- **Clean Architecture :** Séparez strictement la logique métier (Domain), l'application (Services), les routeurs (Présentation) et la base de données (Infrastructure).
- **Validation :** Utilisez toujours Pydantic pour valider les entrées et les sorties.
- **Documentation :** Maintenez Swagger/OpenAPI à jour via les docstrings et les descriptions de routes.
- **Scraping/API ISBN :** Isolez la logique d'appel externe à l'API ISBN dans un service dédié (gestion des erreurs et timeouts) et utilisez **OpenLibrary** comme source unique pour la récupération des métadonnées ISBN.

### 2.2 Frontend : Next.js (React / TypeScript) [web:33][web:34]
- **Structure App Router :** Utilisez le dossier `app/` pour le routage et gardez les composants métier dans `src/components`.
- **Server vs Client Components :** Favorisez les Server Components pour le rendu statique et le SEO. Utilisez `"use client"` uniquement lorsque l'interactivité (hooks, événements) est requise.
- **Gestion des états :** Utilisez React Query (TanStack Query) pour le fetch de données depuis FastAPI afin de gérer le cache et l'état de chargement.
- **Types :** Le code doit être 100% typé. Partagez idéalement les types entre FastAPI (via génération OpenAPI) et Next.js.

## 3. Qualité et Sécurité
- Assurez-vous que toutes les transactions sont restreintes à la devise CHF et livrables uniquement en Suisse.
- Ne pas introduire de bibliothèques tierces superflues sans justification (KISS).

## Paiements et livraison (nouveau)

- **Click & Collect**: Ajout d'une option `CLICK_COLLECT` avec frais fixes `1 CHF`. Les commandes conservent `shipping_method` et `frais_port_chf`.

## Migrations

Créer les scripts de migrations dans le dossier migrations

## 4. Documents LaTeX du dossier de certification (CDA)

Le dépôt contient des documents `.tex` qui constituent le dossier de certification à présenter
au jury (titre Concepteur Développeur d'Applications). Ce ne sont **pas de la documentation
technique classique** : ce sont des livrables évalués, où toute incohérence entre le texte et le
code réel est une non-conformité relevée par le jury.

| Fichier | Rôle |
|---|---|
| `main.tex` | Mémoire de projet — contexte, analyse et conception, réalisation, tests et validation. Contient des extraits de code réels (annexes) et référence les diagrammes de `diagrams/`. |
| `cahier_des_charges.tex` | Cahier des charges autonome — besoin, périmètre (MVP inclus/exclus), spécifications fonctionnelles `SF-XX`, exigences non fonctionnelles, contraintes techniques, recette. |
| `liste_competences.tex` | Traçabilité compétence par compétence entre le référentiel CDA (3 blocs) et les réalisations concrètes du projet, avec niveau d'autonomie. |
| `powerpoint.tex` | Support de soutenance orale (slides Beamer/TikZ), résumé visuel du projet. |
| `diagrams/*.mmd` → `*.pdf` | Diagrammes Mermaid (UML, Merise, architecture, séquence) rendus en PDF et inclus dans `main.tex` / `powerpoint.tex`. |

### Règle de synchronisation obligatoire

**Toute modification du code qui change un comportement, un endpoint, une architecture, un flux
de données ou une intégration externe décrite dans ces documents doit s'accompagner de la mise à
jour des fichiers `.tex` (et du `.mmd` correspondant si un diagramme est concerné) dans le même
changement.**

Concrètement, avant de considérer une tâche terminée, vérifier si le changement touche :
- un endpoint ou son comportement documenté en annexe de `main.tex` ou dans les slides de code de `powerpoint.tex` ;
- une contrainte, une fonctionnalité ou un critère d'acceptation listés dans `cahier_des_charges.tex` ;
- une compétence ou un exemple de mise en œuvre décrit dans `liste_competences.tex` ;
- un flux, une architecture ou une séquence représentés dans un diagramme `diagrams/*.mmd` (ex. : ajout/suppression d'un fournisseur externe, changement de topologie de déploiement, nouvelle étape dans un parcours utilisateur).

Si un diagramme `.mmd` est modifié, régénérer le `.pdf` correspondant (voir `diagrams/render.sh`)
avant de considérer le changement complet. Ne jamais laisser un extrait de code, une URL, un nom
d'endpoint ou une contrainte dans les `.tex` diverger de l'état réel du dépôt.