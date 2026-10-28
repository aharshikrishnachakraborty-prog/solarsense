"""Shared test setup: a temporary login account, so tests never touch the real data/users.json."""

import pytest

from engine import config
from engine.create_users import set_user

TEST_USER, TEST_PASSWORD = "tester", "test-password"


@pytest.fixture(scope="session", autouse=True)
def temp_users_file(tmp_path_factory):
    """Point the users file at a temporary folder and create one test account."""
    config.USERS_FILE = tmp_path_factory.mktemp("users") / "users.json"
    set_user(TEST_USER, TEST_PASSWORD)


def log_in(client):
    """Log the test client in (it keeps the session cookie for later requests)."""
    response = client.post("/api/login", json={"username": TEST_USER, "password": TEST_PASSWORD})
    assert response.status_code == 200
