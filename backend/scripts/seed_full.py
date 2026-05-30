#!/usr/bin/env python3
"""Seed the database with default catalog data for development.

Creates: TypeObjet, EtatUsure, Categorie, SourceStock and a sample Article/Livre + Stock.
Idempotent: will not create duplicates when re-run.
"""
from __future__ import annotations

import os
import sys
# Ensure the `backend/` package directory is on sys.path so imports like
# `from infrastructure import models` resolve when running this script
# directly (regardless of current working directory).
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from infrastructure.db import SessionLocal
from infrastructure import models
from infrastructure import crud_user
from datetime import date


def get_or_create(db, model, **kwargs):
    obj = db.query(model).filter_by(**{k: kwargs[k] for k in kwargs if k in model.__table__.columns.keys()}).first()
    if obj:
        return obj
    obj = model(**{k: v for k, v in kwargs.items() if k in model.__table__.columns.keys()})
    db.add(obj)
    db.flush()
    return obj


def seed_full():
    db = SessionLocal()
    try:
        # TypeObjet
        to_book = db.query(models.TypeObjet).filter(models.TypeObjet.code == 'BOOK').first()
        if not to_book:
            to_book = models.TypeObjet(libelle='Livre', code='BOOK', description='Type par défaut (Livre)')
            db.add(to_book)
            db.flush()

        # EtatUsure defaults
        for lib in ('Neuf', 'Bon état', 'Usagé'):
            e = db.query(models.EtatUsure).filter(models.EtatUsure.libelle == lib).first()
            if not e:
                db.add(models.EtatUsure(libelle=lib, description=f'Défaut: {lib}'))
        db.flush()

        # Categories
        for cat in ('Fiction', 'Non-fiction', 'Sciences'):
            c = db.query(models.Categorie).filter(models.Categorie.libelle == cat).first()
            if not c:
                db.add(models.Categorie(libelle=cat, description=f'Catégorie {cat}'))
        db.flush()

        # SourceStock default
        ss = db.query(models.SourceStock).filter(models.SourceStock.libelle == 'Default').first()
        if not ss:
            ss = models.SourceStock(libelle='Default', type_source='ADMIN', description='Source par défaut')
            db.add(ss)
            db.flush()

        # Sample article + livre + stock (idempotent by isbn)
        sample_isbn = '9780143127741'
        existing = db.query(models.Livre).filter(models.Livre.isbn == sample_isbn).first()
        if not existing:
            etat_bon = db.query(models.EtatUsure).filter(models.EtatUsure.libelle == 'Bon état').first()
            if not etat_bon:
                raise ValueError("EtatUsure 'Bon état' not found; run seed_full.py first")
            article = models.Article(
                id_type_objet=to_book.id_type_objet,
                id_etat_usure=etat_bon.id_etat_usure,
                sku=sample_isbn,
                titre='Sample Seed Book',
                description='Example seeded book',
                image_link=None,
                prix_chf=12.5,
                actif=True,
            )
            db.add(article)
            db.flush()
            livre = models.Livre(id_article=article.id_article, isbn=sample_isbn, auteur='Seed Author')
            db.add(livre)
            db.flush()
            stock = models.Stock(id_article=article.id_article, id_source_stock=ss.id_source_stock, quantite_disponible=3, quantite_reservee=0)
            db.add(stock)

        # Create admin user if not present
        admin_email = os.getenv('ADMIN_EMAIL', 'admin@example.com')
        admin_password = os.getenv('ADMIN_PASSWORD', 'admin1234!')
        if not admin_password or admin_password == 'admin1234!':
            import secrets
            admin_password = secrets.token_urlsafe(12)
            print(f"Generated admin password: {admin_password}")
        existing_user = db.query(models.Utilisateur).filter(models.Utilisateur.email == admin_email).first()
        if not existing_user:
            crud_user.create_user(db, {
                "nom": "Admin",
                "prenom": "User",
                "email": admin_email,
                "mot_de_passe": admin_password,
                "role": "admin",
            })
            print(f'Admin user created: {admin_email}')

        db.commit()
        print('Seed completed.')
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == '__main__':
    seed_full()
