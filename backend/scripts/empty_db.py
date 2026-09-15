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
    # Guard against running this against a real database by accident (e.g. a
    # production `.env` sourced into the shell out of habit). Not reachable
    # via any API route, so this only protects the deliberate/manual case --
    # but that's exactly the case where a wrong-env mistake actually happens.
    env = os.getenv('ENVIRONMENT', 'development').strip().lower()
    if env not in ('development', 'test'):
        print(
            f"Refusing to empty the database: ENVIRONMENT={env!r} is not "
            "'development' or 'test'. Set ENVIRONMENT explicitly if this is "
            "really what you want.",
            file=sys.stderr,
        )
        sys.exit(1)

    db = SessionLocal()
    try:
        print('Deleting all data from database (foreign key checks disabled)')
        db.execute(text('SET FOREIGN_KEY_CHECKS=0;'))
        tables = [
            'scan_isbn',
            'paiement',
            'stock_mouvement',
            'ligne_commande',
            'commande',
            'stock',
            'livre',
            'article',
            'utilisateur',
            'source_stock',
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
