# -*- coding: utf-8 -*-
import sys

import requests

BASE = "http://localhost:8080"


def main() -> int:
    login = requests.get(f"{BASE}/login", timeout=10)
    print(f"login page: {login.status_code}")
    print(f"  Google button: {'Google' in login.text}")
    print(f"  email form: {'type=\"email\"' in login.text}")

    google = requests.get(f"{BASE}/login/google", allow_redirects=False, timeout=10)
    location = google.headers.get("Location", "")
    print(f"/login/google: {google.status_code}")
    print(f"  redirect: {location[:200]}")
    print(f"  -> Google OAuth: {'accounts.google.com' in location}")

    unauth = requests.get(f"{BASE}/communities", allow_redirects=False, timeout=10)
    print(f"/communities (未ログイン): {unauth.status_code}")
    print(f"  redirect: {unauth.headers.get('Location', '')[:120]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
