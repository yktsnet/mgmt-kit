"""ログイン。Sign in with Google の ID トークンを確かめ、署名した Cookie でログインの状態を持つ。

通すのは、許可した Google Workspace のドメインのアカウントで、在籍者にいる人だけである。
デモでは Google を通らず、在籍者から1人を選んでログインする。
"""

import base64
import hashlib
import hmac
import json
import time

COOKIE = "board_session"
SESSION_TTL = 7 * 24 * 3600


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def issue(key: bytes, email: str, now: float | None = None) -> str:
    payload = _b64(json.dumps({"e": email, "x": int((now or time.time()) + SESSION_TTL)}).encode())
    sig = _b64(hmac.new(key, payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{sig}"


def verify(key: bytes, value: str | None, now: float | None = None) -> str | None:
    """署名と期限が正しければメールを返す。"""
    if not value or "." not in value:
        return None
    payload, sig = value.split(".", 1)
    expected = _b64(hmac.new(key, payload.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(sig, expected):
        return None
    try:
        data = json.loads(_unb64(payload))
    except ValueError:
        return None
    if data.get("x", 0) < (now or time.time()):
        return None
    return data.get("e")


def verify_google(credential: str, client_id: str, domain: str) -> str | None:
    """ID トークンを確かめ、許可したドメインの Workspace アカウントならメールを返す。"""
    from google.auth.transport import requests as grequests
    from google.oauth2 import id_token

    try:
        claims = id_token.verify_oauth2_token(credential, grequests.Request(), client_id)
    except ValueError:
        return None
    # hd は Workspace のアカウントにだけ付く。メールの末尾だけで判定すると、個人の Google アカウントも通る
    if claims.get("hd") != domain or not claims.get("email_verified"):
        return None
    email = str(claims.get("email", "")).lower()
    return email if email.endswith(f"@{domain}") else None
