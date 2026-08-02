"""
Unit tests for infrastructure.crud_book
"""
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock
from  infrastructure import crud_book
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../backend')))

class TestCrudBook(unittest.TestCase):
    def setUp(self):
        self.db = MagicMock()
        # crud_book only reads attributes off its `book` argument (duck-typed),
        # so a plain namespace matching BookCreate's shape is enough here.
        self.book = SimpleNamespace(
            id_article=1,
            id_type_objet=0,
            id_etat_usure=0,
            titre="Test Book",
            isbn="1234567890",
            auteur="Author",
            editeur="Editor",
            date_publication=None,
            langue="FR",
            description="Desc",
            image_link="http://img",
            prix_chf=10.0,
            actif=True,
        )

    def test_get_books(self):
        self.db.query().all.return_value = []
        result = crud_book.get_books(self.db)
        self.assertEqual(result, [])

    def test_get_book(self):
        self.db.query().filter().first.return_value = self.book
        result = crud_book.get_book(self.db, 1)
        self.assertEqual(result, self.book)

    def test_create_book(self):
        # Only checks that the function runs without error with mock
        self.db.add = MagicMock()
        self.db.flush = MagicMock()
        self.db.commit = MagicMock()
        self.db.refresh = MagicMock()
        self.db.query().filter().first.return_value = None
        crud_book.create_book(self.db, self.book)
        self.db.add.assert_called()
        self.db.commit.assert_called()

    def test_update_book_not_found(self):
        self.db.query().filter().first.return_value = None
        result = crud_book.update_book(self.db, 1, {"titre": "New"}) # type: ignore
        self.assertIsNone(result)

    def test_delete_book_not_found(self):
        self.db.query().filter().first.return_value = None
        result = crud_book.delete_book(self.db, 1)
        self.assertFalse(result)

if __name__ == "__main__":
    unittest.main()
