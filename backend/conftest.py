# backend/conftest.py
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Running pytest locally must never touch the same database the dev server
# serves from: TestClient(app) exercises the real app against the real
# configured MYSQL_DB, and nothing here ever cleans up what a test creates.
# Confirmed in practice -- dozens of test fixtures (dummy books with
# image_link values like "http://img"/"http://img.integration", titles like
# "Article title"/"Scan Book") had accumulated as permanent rows in the actual
# dev catalog, showing up as CSP-blocked broken images in the real app.
# This must be set before `infrastructure.db` (or anything importing it) is
# ever imported, since it reads MYSQL_DB from the environment at import time
# -- conftest.py is collected first, so this is early enough.
# CI already provisions its own disposable MySQL service container per run
# (GITHUB_ACTIONS is set there) and is unaffected by this.
if not os.getenv("GITHUB_ACTIONS"):
    os.environ["MYSQL_DB"] = os.getenv("MYSQL_DB", "caribooks") + "_test"