"""Create or change login accounts for the dashboard.

Run from the solarsense folder:
    python -m engine.create_users                    # create the demo accounts (config.DEMO_USERS)
    python -m engine.create_users NAME PASSWORD      # add one user, or change their password
Passwords are saved only as a salted hash in data/users.json — never as plain text.
"""

import hashlib
import hmac
import json
import secrets

from engine import config


def hash_password(password, salt):
    """Turn a password into a hash that cannot be turned back (PBKDF2-SHA256)."""
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt),
                               config.PASSWORD_ITERATIONS).hex()


def load_users():
    """All accounts as {username: {"salt": ..., "hash": ...}} (empty if the file does not exist)."""
    if not config.USERS_FILE.exists():
        return {}
    return json.loads(config.USERS_FILE.read_text(encoding="utf-8"))


def set_user(username, password):
    """Add a user or change their password (a new random salt every time)."""
    users = load_users()
    salt = secrets.token_hex(16)
    users[username] = {"salt": salt, "hash": hash_password(password, salt)}
    config.USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    config.USERS_FILE.write_text(json.dumps(users, indent=2), encoding="utf-8")


def check_password(username, password):
    """True if this username exists and the password matches its hash."""
    user = load_users().get(username)
    if user is None:
        return False
    # compare_digest takes the same time whether the first or last character is wrong (no timing hints).
    return hmac.compare_digest(hash_password(password, user["salt"]), user["hash"])


def ensure_demo_users():
    """Create the demo accounts if no users file exists yet (first run, or a fresh server)."""
    if not config.USERS_FILE.exists():
        for username, password in config.DEMO_USERS.items():
            set_user(username, password)


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 3:
        set_user(sys.argv[1], sys.argv[2])
        print(f"Saved user '{sys.argv[1]}' in {config.USERS_FILE}")
    elif len(sys.argv) == 1:
        for name, secret in config.DEMO_USERS.items():
            set_user(name, secret)
        print(f"Demo users {list(config.DEMO_USERS)} saved in {config.USERS_FILE}")
    else:
        print("Usage: python -m engine.create_users [NAME PASSWORD]")
