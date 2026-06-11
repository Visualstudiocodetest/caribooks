#!/usr/bin/env python3
"""Seed the database with default catalog data for development.

Idempotent — safe to re-run; will not create duplicates.

Usage:
    python scripts/seed_full.py
    ADMIN_EMAIL=admin@myapp.com ADMIN_PASSWORD=secret python scripts/seed_full.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from infrastructure.db import SessionLocal
from infrastructure import models, crud_user


def upsert(db, model, lookup_field: str, lookup_value, **fields):
    """Get or create a model instance by a single lookup field."""
    obj = db.query(model).filter(getattr(model, lookup_field) == lookup_value).first()
    if not obj:
        obj = model(**{lookup_field: lookup_value, **fields})
        db.add(obj)
        db.flush()
    return obj


def seed():
    db = SessionLocal()
    try:
        # ── Type objets ──────────────────────────────────────────────────────
        upsert(db, models.TypeObjet, 'code', 'BOOK', libelle='Livre')
        upsert(db, models.TypeObjet, 'code', 'DVD',  libelle='DVD')

        # ── États d'usure ────────────────────────────────────────────────────
        for lib in ('Neuf', 'Très bon état', 'Bon état', 'Usagé'):
            upsert(db, models.EtatUsure, 'libelle', lib)

        # ── Catégories ───────────────────────────────────────────────────────
        for lib in ('Fiction', 'Non-fiction', 'Sciences', 'Jeunesse', 'Histoire', 'Biographie'):
            upsert(db, models.Categorie, 'libelle', lib)

        # ── Source stock par défaut ──────────────────────────────────────────
        ss = upsert(db, models.SourceStock, 'libelle', 'Magasin', type_source='ADMIN')

        # ── Livre de démonstration ───────────────────────────────────────────
        SAMPLE_ISBN = '9780062316097'
        if not db.query(models.Livre).filter(models.Livre.isbn == SAMPLE_ISBN).first():
            to_book = db.query(models.TypeObjet).filter(models.TypeObjet.code == 'BOOK').first()
            etat    = db.query(models.EtatUsure).filter(models.EtatUsure.libelle == 'Bon état').first()
            article = models.Article(
                id_type_objet=to_book.id_type_objet,
                id_etat_usure=etat.id_etat_usure,
                sku=SAMPLE_ISBN,
                titre='The Alchemist',
                description="A shepherd's journey toward his personal legend.",
                image_link=None,
                prix_chf=9.90,
                actif=True,
            )
            db.add(article)
            db.flush()
            db.add(models.Livre(id_article=article.id_article, isbn=SAMPLE_ISBN, auteur='Paulo Coelho'))
            db.flush()
            db.add(models.Stock(
                id_article=article.id_article,
                id_source_stock=ss.id_source_stock,
                quantite_disponible=5,
                quantite_reservee=0,
            ))

        # ── Compte admin ─────────────────────────────────────────────────────
        admin_email    = os.getenv('ADMIN_EMAIL', 'admin@caribooks.ch')
        admin_password = os.getenv('ADMIN_PASSWORD', '')
        if not admin_password:
            import secrets
            admin_password = secrets.token_urlsafe(14)
            print(f'[seed] Admin password generated: {admin_password}')

        if not db.query(models.Utilisateur).filter(models.Utilisateur.email == admin_email).first():
            crud_user.create_user(db, {
                'nom': 'Admin',
                'prenom': 'Caribooks',
                'email': admin_email,
                'mot_de_passe': admin_password,
                'role': 'admin',
            })
            print(f'[seed] Admin account created: {admin_email}')

        db.commit()
        print('[seed] Done.')
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == '__main__':
    seed()
