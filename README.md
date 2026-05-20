# Caribooks - Plateforme E-Commerce Solidaire

![Next.js](https://img.shields.io/badge/Next.js-15-black?style=flat&logo=next.js)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat&logo=fastapi)
![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat&logo=python)

## 📖 Contexte du Projet

**Caribooks** est une plateforme de vente en ligne de livres de seconde main, développée pour **Caritas**. Ce projet a été initié pour résoudre le problème des livres invendus dans les recycleries, dont les bénéfices financent la réinsertion professionnelle.

### Contraintes spécifiques :
- **Devise unique :** Toutes les transactions sont exclusivement en Francs Suisses (CHF).
- **Zone géographique :** La livraison est strictement limitée à la Suisse.
- **Ergonomie bénévole :** Le back-office intègre un système d'ajout rapide de livres au catalogue via un scan de code ISBN.

---

## 🏗 Architecture du Projet


Le projet suit les principes **SOLID**, **Clean Architecture** et **KISS**, et est divisé en deux parties principales :

**⚠️ Contraintes techniques supplémentaires :**
- **Base de données :** L'application fonctionne exclusivement avec une base de données **mySQL** (et non SQLite ou PostgreSQL).
- **API ISBN :** Toutes les métadonnées des livres sont récupérées via l'API **OpenLibrary** (https://openlibrary.org/dev/docs/api/books).

1. **Backend (API REST) - `FastAPI` :** 
   - Gère la logique métier, la base de données, l'authentification et l'intégration avec l'API ISBN pour récupérer les métadonnées des livres.
2. **Frontend - `Next.js` :** 
   - Offre une interface utilisateur fluide pour les clients finaux (vitrine e-commerce) et un back-office simplifié pour les bénévoles de Caritas.

---

## 🚀 Installation et Lancement en local

### Prérequis
- Node.js (v18+)
- Python (v3.11+)
- Git

### 1. Cloner le dépôt
```bash
git clone https://github.com/votre-utilisateur/caribooks.git
cd caribooks
```

### 2. Lancer le Backend (FastAPI)
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Sur Windows : venv\Scripts\activate
pip install -r requirements.txt
# Copier le fichier d'environnement et configurer la BDD
cp .env.example .env
uvicorn main:app --reload
```
*L'API sera disponible sur : http://localhost:8000* (Documentation Swagger sur `/docs`)

### 3. Lancer le Frontend (Next.js)
```bash
cd ../frontend
npm install
# Configurer les variables d'environnement (API URL, etc.)
cp .env.example .env.local
npm run dev
```
*Le site web sera accessible sur : http://localhost:3000*

---

## 👨‍💻 Principes de Développement

Nous appliquons les meilleures pratiques de l'industrie :
- **KISS (Keep It Simple, Stupid) :** Nous privilégions un code simple, lisible et facile à maintenir.
- **SOLID :** Notre architecture backend (Clean Architecture) et frontend respecte strictement les principes SOLID pour garantir la scalabilité du projet.
- **KKS Structuration :** Une hiérarchie claire et standardisée des dossiers, fichiers et logs.

Pour plus de détails sur les conventions de code, veuillez consulter le fichier `AGENTS.md`.