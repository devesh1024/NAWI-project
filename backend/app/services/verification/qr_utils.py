"""
QR code generation for report verification.

Each generated report gets a QR code encoding a URL to the public verify
page: FRONTEND_URL/verify/<test_session_id>. Anyone scanning it with a phone
camera lands on a page showing the canonical database record for that
report — a quick/"light" check, not a cryptographic one (see
verify_routes.py's docstring for why that distinction matters).
"""
import io
import os
import qrcode


def verification_url(test_session_id: str) -> str:
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
    return f"{frontend_url}/verify/{test_session_id}"


def generate_qr_png_bytes(test_session_id: str) -> bytes:
    """Returns PNG bytes of a QR code encoding the verification URL."""
    img = qrcode.make(verification_url(test_session_id))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
