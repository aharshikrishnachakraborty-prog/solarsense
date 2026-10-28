"""Checks the login: pages and API are locked until you log in, and passwords are stored safely."""

import json

import pytest
from fastapi.testclient import TestClient

from engine import config
from engine.create_users import check_password
from tests.conftest import TEST_PASSWORD, TEST_USER, log_in


@pytest.fixture
def client():
    """A fresh test client with NO session cookie."""
    if not config.ALERTS_FILE.exists():
        pytest.skip("Run the pipeline first (python run_all.py)")
    from api.main import app
    with TestClient(app) as test_client:
        yield test_client


def test_locked_without_login(client):
    """No login: the API answers 401 and pages send you to the login page."""
    assert client.get("/api/plants").status_code == 401
    page = client.get("/plant.html", follow_redirects=False)
    assert page.status_code == 303 and page.headers["location"] == "login.html?next=plant.html"
    assert client.get("/", follow_redirects=False).headers["location"] == "login.html?next=index.html"


def test_login_page_and_health_stay_open(client):
    """You can always reach the login page, its styles and the health check."""
    for path in ["/login.html", "/css/style.css", "/js/login.js", "/api/health"]:
        assert client.get(path).status_code == 200


def test_wrong_password_is_refused(client):
    """A wrong password (or unknown user) gets 401 and no cookie."""
    for name, secret in [(TEST_USER, "nope"), ("nobody", TEST_PASSWORD)]:
        response = client.post("/api/login", json={"username": name, "password": secret})
        assert response.status_code == 401
        assert config.SESSION_COOKIE not in response.cookies


def test_login_then_logout(client):
    """Login opens everything; logout locks it again."""
    log_in(client)
    assert client.get("/api/me").json() == {"username": TEST_USER}
    assert client.get("/api/plants").status_code == 200
    assert client.get("/index.html").status_code == 200
    client.post("/api/logout")
    assert client.get("/api/plants").status_code == 401


def test_passwords_are_hashed():
    """The users file never contains the real password."""
    text = config.USERS_FILE.read_text(encoding="utf-8")
    assert TEST_PASSWORD not in text
    assert set(json.loads(text)[TEST_USER]) == {"salt", "hash"}
    assert check_password(TEST_USER, TEST_PASSWORD) and not check_password(TEST_USER, TEST_PASSWORD + "x")


def test_app_install_files_open_without_login(client):
    """The installable-app files (manifest, service worker, icons) load before logging in."""
    manifest = client.get("/manifest.webmanifest")
    assert manifest.status_code == 200 and manifest.headers["content-type"].startswith("application/manifest+json")
    body = manifest.json()
    assert body["display"] == "standalone" and body["start_url"] == "index.html"
    assert any(icon["sizes"] == "512x512" for icon in body["icons"])
    assert client.get("/sw.js").status_code == 200
    assert client.get("/icons/icon-512.png").headers["content-type"] == "image/png"
