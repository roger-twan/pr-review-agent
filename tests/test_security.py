import hashlib
import hmac

from app.security import verify_github_signature


def test_verify_github_signature_accepts_valid_sha256_signature() -> None:
    secret = "top-secret"
    payload = b'{"zen":"Keep it logically awesome."}'
    digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()

    assert verify_github_signature(secret, payload, f"sha256={digest}")


def test_verify_github_signature_rejects_missing_or_invalid_signature() -> None:
    assert not verify_github_signature("secret", b"payload", None)
    assert not verify_github_signature("secret", b"payload", "sha1=abc")
    assert not verify_github_signature("secret", b"payload", "sha256=wrong")

