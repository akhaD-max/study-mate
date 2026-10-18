"""Создать локальный .env со случайными секретами без перезаписи существующего."""

import secrets
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent.parent
    destination = root / ".env"
    if destination.exists():
        print(".env уже существует, оставлен без изменений.")
        return
    content = (root / ".env.example").read_text(encoding="utf-8")
    content = content.replace(
        "DJANGO_SECRET_KEY=\n", f"DJANGO_SECRET_KEY={secrets.token_urlsafe(64)}\n"
    ).replace(
        "POSTGRES_PASSWORD=\n", f"POSTGRES_PASSWORD={secrets.token_urlsafe(32)}\n"
    )
    with destination.open("x", encoding="utf-8", newline="\n") as output:
        output.write(content)
    print("Создан .env с локальными секретами.")


if __name__ == "__main__":
    main()
