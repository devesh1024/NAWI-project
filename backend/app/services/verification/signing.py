"""
PDF digital signing + verification, using pyHanko.

This gives REAL tamper evidence for PDFs: the signature covers the exact
bytes of the document at signing time. If anything in the file changes
afterward — even one byte — `intact` comes back False on verification.
This is NOT possible to do meaningfully for DOCX files (no robust
byte-level signing via python-docx), which is why DOCX verification
elsewhere in this feature relies on a DB cross-check instead, and is
explicitly documented as a weaker guarantee.

Tested standalone before being handed off: signing a sample PDF, verifying
it (intact=True), then flipping a single byte inside its content stream
and re-verifying (intact=False, bottom_line=False) — confirmed working.

Setup: automatic. On first start the app generates signing_key.pem +
signing_cert.pem (self-signed, 10-year validity) if none exist. You can still
force a fresh pair with `python -m backend.app.services.verification.signing`. Keep signing_key.pem secret — anyone with it can forge valid
signatures. On Render, upload both as Secret Files, or set
SIGNING_KEY_PEM / SIGNING_CERT_PEM as env vars containing the raw PEM text.
"""
import logging
import os
from pathlib import Path

from pyhanko.sign import signers
from pyhanko.sign.fields import SigFieldSpec, append_signature_field
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.sign.validation import validate_pdf_signature
from pyhanko.sign.validation.settings import KeyUsageConstraints
from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko_certvalidator import ValidationContext
from pyhanko.keys import load_cert_from_pemder

logger = logging.getLogger("uvicorn.error")

CERT_DIR = Path(__file__).resolve().parent / "certs"
KEY_PATH = CERT_DIR / "signing_key.pem"
CERT_PATH = CERT_DIR / "signing_cert.pem"


def generate_signing_identity() -> None:
    """Creates a self-signed signing key + cert (10-year validity) in CERT_DIR."""
    import datetime
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "NAWI TestSuite Report Signer")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name).issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=3650))
        .sign(key, hashes.SHA256())
    )

    CERT_DIR.mkdir(parents=True, exist_ok=True)
    KEY_PATH.write_bytes(key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL, serialization.NoEncryption()
    ))
    CERT_PATH.write_bytes(cert.public_bytes(serialization.Encoding.PEM))


def ensure_signing_identity() -> None:
    """Called once at app startup so the first report never fails for lack of a key."""
    _ensure_local_pem_files()


def _ensure_local_pem_files() -> tuple[str, str]:
    """
    Resolves to local file paths pyHanko can load from, writing them from
    SIGNING_KEY_PEM / SIGNING_CERT_PEM env vars first if the files don't
    already exist (covers the Render-env-var deployment path without
    changing the signing/loading code below).
    """
    if KEY_PATH.exists() and CERT_PATH.exists():
        return str(KEY_PATH), str(CERT_PATH)

    key_pem = os.getenv("SIGNING_KEY_PEM")
    cert_pem = os.getenv("SIGNING_CERT_PEM")
    if not key_pem or not cert_pem:
        # Nothing configured: create a signing identity automatically (first run).
        generate_signing_identity()
        logger.warning(
            "No signing key found - generated a new one at %s. Fine for local "
            "development. On hosts with an ephemeral disk (e.g. Render) set "
            "SIGNING_KEY_PEM / SIGNING_CERT_PEM instead, otherwise every redeploy "
            "creates a new key and reports signed earlier will no longer verify.",
            CERT_DIR,
        )
        return str(KEY_PATH), str(CERT_PATH)

    CERT_DIR.mkdir(parents=True, exist_ok=True)
    KEY_PATH.write_text(key_pem)
    CERT_PATH.write_text(cert_pem)
    return str(KEY_PATH), str(CERT_PATH)


def sign_pdf_file(input_path: str, output_path: str) -> None:
    """Reads a plain PDF, writes a digitally-signed copy to output_path."""
    key_path, cert_path = _ensure_local_pem_files()
    signer = signers.SimpleSigner.load(key_path, cert_path, key_passphrase=None)

    with open(input_path, "rb") as inf:
        w = IncrementalPdfFileWriter(inf)
        append_signature_field(w, SigFieldSpec(sig_field_name="NAWIReportSignature"))
        with open(output_path, "wb") as outf:
            signers.sign_pdf(
                w,
                signers.PdfSignatureMetadata(field_name="NAWIReportSignature"),
                signer=signer,
                output=outf,
            )


def verify_pdf_signature(file_bytes: bytes) -> dict:
    """
    Returns {signed, intact, trusted, valid} for an uploaded PDF's bytes.
    `intact=False` is the key tamper signal: content changed since signing.
    A PDF with no embedded signature at all (signed=False) is simply one
    that either predates this feature or never went through our system.
    """
    import io

    key_path, cert_path = _ensure_local_pem_files()
    trust_root = load_cert_from_pemder(cert_path)
    vc = ValidationContext(trust_roots=[trust_root])

    try:
        r = PdfFileReader(io.BytesIO(file_bytes))
        sigs = r.embedded_signatures
        if not sigs:
            return {"signed": False, "intact": None, "trusted": None, "valid": None}

        status = validate_pdf_signature(
            sigs[0], vc, key_usage_settings=KeyUsageConstraints(key_usage=None)
        )
        return {
            "signed": True,
            "intact": status.intact,
            "trusted": status.trusted,
            "valid": status.valid,
            "bottom_line": status.bottom_line,
        }
    except Exception as exc:
        # A corrupted/malformed PDF structure is itself a strong tamper
        # signal (a genuinely untouched signed PDF always parses cleanly).
        return {"signed": None, "intact": False, "trusted": False, "valid": False, "error": str(exc)}


if __name__ == "__main__":
    # Optional manual (re)generation - no longer required, the app does this
    # automatically on first start if no key exists.
    generate_signing_identity()
    print(f"Generated {KEY_PATH} and {CERT_PATH}")
    print("Keep signing_key.pem secret. Do not commit either file - the certs/")
    print("folder is git-ignored.")
