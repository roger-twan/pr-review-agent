import hashlib
import hmac


def verify_github_signature(secret: str, payload: bytes, signature_header: str | None) -> bool:
    if not signature_header:
        return False

    prefix = "sha256="
    if not signature_header.startswith(prefix):
        return False

    expected = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    received = signature_header.removeprefix(prefix)
    return hmac.compare_digest(expected, received)

