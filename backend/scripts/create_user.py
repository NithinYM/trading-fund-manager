from __future__ import annotations

import argparse
from getpass import getpass
from hashlib import sha256
from pathlib import Path
import sys
from uuid import uuid4

import bcrypt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.database import SessionLocal
from app.models.user import User


def password_hash(password: str) -> str:
    return bcrypt.hashpw(sha256(password.encode("utf-8")).digest(), bcrypt.gensalt()).decode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a Trading Fund Manager user")
    parser.add_argument("--username", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--role", choices=("ADMIN", "MANAGER", "TRADER"), default="ADMIN")
    args = parser.parse_args()
    password = getpass("Password: ")
    confirmation = getpass("Confirm password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match")

    with SessionLocal() as db:
        if db.query(User).filter((User.username == args.username) | (User.email == args.email)).first() is not None:
            raise SystemExit("A user with this username or email already exists")
        db.add(
            User(
                id=str(uuid4()),
                username=args.username,
                email=args.email,
                password_hash=password_hash(password),
                role=args.role,
                is_active=True,
            )
        )
        db.commit()
    print(f"Created {args.role} user: {args.username}")


if __name__ == "__main__":
    main()
