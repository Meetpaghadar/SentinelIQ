import getpass

from sqlalchemy import select

from sentineliq.auth.passwords import hash_password
from sentineliq.db.session import SessionLocal
from sentineliq.models import User


def main() -> None:
    email = input("User email: ").strip()
    password = getpass.getpass("New password: ")

    if len(password) < 8:
        raise ValueError("Password must contain at least 8 characters")

    with SessionLocal() as session:
        user = session.scalar(select(User).where(User.email == email))

        if user is None:
            raise ValueError("User not found")

        user.password_hash = hash_password(password)
        session.commit()

    print("Password updated.")


if __name__ == "__main__":
    main()
