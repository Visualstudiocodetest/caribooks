# Caribooks — Backlog d'améliorations (feature TODO)

Idées d'évolutions classées par valeur/effort. Toutes respectent les contraintes
projet : devise **CHF uniquement**, livraison **Suisse uniquement**, base **MySQL**,
métadonnées ISBN via **OpenLibrary**, principes **SOLID / KISS**.

## Déjà livré dans cette itération
- [x] **Recherche + filtres catalogue** — recherche titre/auteur/ISBN, filtres état
      d'usure et catégorie, tri, **fourchette de prix (min/max CHF)**. `CatalogClient.tsx`.
- [x] **Endpoint de disponibilité groupé** `GET /stock/availability` (corrige le N+1).
- [x] **React Query** pour le fetch client (cache/dedup/retry).

## Prioritaire (valeur haute)
- [ ] **Liste de souhaits / favoris** — table `favori(id_utilisateur, id_article, date_ajout)`,
      endpoints `GET/POST/DELETE /users/me/favoris`, bouton cœur sur `BookCard`, page `/account/favoris`.
      Migration SQL dédiée dans `backend/migrations/`.
- [ ] **Alerte réappro** ("prévenez-moi quand disponible") — table `alerte_stock`, déclenchée
      à la remise en stock (dans `stock_router` increment / `_add_one_to_stock`), envoi e-mail.
- [ ] **Tableau de bord admin (ventes)** — CA en CHF, top titres, alertes stock bas.
      Nouveau `GET /orders/admin/stats` (agrégations SQL) + page `/admin`.
- [ ] **Facture PDF** à la finalisation de commande — génération serveur (reportlab/weasyprint),
      lien de téléchargement depuis `/account/orders`.

## Moyen terme
- [ ] **Suivi de commande (timeline client)** — visualiser la machine à états
      (`OPEN → PAID → SENT/AT_RECEPTION → FINISHED`) déjà centralisée dans `order_service`.
- [ ] **Avis / notes** (modérés) sur les livres — table `avis`, modération admin.
- [ ] **Codes promo** — CHF uniquement, Suisse uniquement ; validation serveur du montant.
- [ ] **Recommandations** ("livres similaires") par catégorie / auteur.
- [ ] **i18n** (fr/de/it) pour la Suisse, en s'appuyant sur le travail RGPD/accessibilité existant.

## Dette technique restante (repérée pendant la revue)
- [ ] **Décomposer les god components** : `PaymentClient.tsx` (~470 l.) → hooks
      `usePostFinanceHandler` / `useCountdown` + présentation ; `admin/books/new` (~400 l.)
      → hook scanner/caméra + autofill OpenLibrary. (Reporté : zone de paiement fragile, à
      faire avec une couverture de tests renforcée.)
- [ ] **Composant générique de liste-CRUD admin** pour remplacer les 4 pages quasi
      identiques `admin/lists/*` (categories, etat-usures, type-objets, article-categories).
- [ ] **Rate limiter partagé (Redis)** — l'actuel est en mémoire par worker ; suffisant pour
      une VM unique, à remplacer si passage multi-instances.
- [ ] **Dockerfile** : ajouter un superviseur de process (ou séparer backend/frontend en deux
      conteneurs) pour qu'une mort du backend ne laisse pas un conteneur à moitié up.
- [ ] **Source unique du schéma** : aligner `Schema.SQL`, les modèles ORM et les migrations
      (aujourd'hui trois sources ; CI bootstrap via `create_all`, prod via `Schema.SQL`).
