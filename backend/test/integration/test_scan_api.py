from __future__ import annotations

from fastapi.testclient import TestClient


def test_scan_isbn_crud(client: TestClient, register_and_login, uniq: str):
    user_headers = register_and_login(f"scan_{uniq}@example.com")
    admin_headers = register_and_login(f"scan_admin_{uniq}@example.com", role="admin")

    # Need a book (livre) to scan against
    r = client.post(
        "/books/",
        json={
            "titre": "Scan Book",
            "isbn": f"ISBN_{uniq}",
            "auteur": "A",
            "editeur": "E",
            "langue": "FR",
            "description": "D",
            "image_link": "http://img",
            "prix_chf": 10.0,
            "actif": True,
        },
        headers=admin_headers,
    )
    assert r.status_code == 201, r.text
    book_id = r.json()["id_article"]

    r = client.post(
        "/scans/",
        json={"id_article_livre": book_id, "isbn_lu": f"ISBN_{uniq}", "valide": False},
        headers=user_headers,
    )
    assert r.status_code == 201, r.text
    scan = r.json()

    assert client.get("/scans/", headers=user_headers).status_code == 200
    assert client.get(f"/scans/{scan['id_scan_isbn']}", headers=user_headers).status_code == 200

    r = client.put(f"/scans/{scan['id_scan_isbn']}", json={"valide": True}, headers=user_headers)
    assert r.status_code == 200
    assert r.json()["valide"] is True

    assert client.delete(f"/scans/{scan['id_scan_isbn']}", headers=user_headers).status_code == 204

