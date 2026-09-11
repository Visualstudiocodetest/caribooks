#!/usr/bin/env python3
"""Empty the database (development only).

This script will delete rows from main tables. Use with caution.
"""
from __future__ import annotations

import os
import sys

# Ensure the `backend/` package directory is on sys.path so imports like
# `from infrastructure.db import SessionLocal` work when running this script
# directly (regardless of current working directory).
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import text

from infrastructure.db import SessionLocal


def empty_db():
    db = SessionLocal()
    try:
        print('Deleting all data from database (foreign key checks disabled)')
        db.execute(text('SET FOREIGN_KEY_CHECKS=0;'))
        tables = [
            'scan_isbn',
            'paiement',
            'ligne_commande',
            'commande',
            'stock',
            'article_categorie',
            'livre',
            'article',
            'utilisateur',
            'source_stock',
            'categorie',
            'etat_usure',
            'type_objet',
        ]
        for t in tables:
            db.execute(text(f'DELETE FROM {t};'))
        db.execute(text('SET FOREIGN_KEY_CHECKS=1;'))
        db.commit()
        print('Empty DB completed.')
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == '__main__':
    empty_db()
