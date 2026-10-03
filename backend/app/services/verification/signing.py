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
import re as _re
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


_SECRET_FILES_DIR = Path("/etc/secrets")     # where Render mounts "Secret Files"
_resolved: tuple[str, str] | None = None


def _normalize_pem(text: str) -> str:
    """
    Rebuilds a clean PEM from text that was damaged on its way through an env
    var / dashboard: line breaks collapsed to spaces, literal "\\n" sequences,
    surrounding quotes, Windows line endings, everything on one line, etc.
    """
    t = text.strip().strip("\"'").strip()
    t = t.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\r\n", "\n").replace("\r", "\n")
    m = _re.search(r"-----BEGIN ([A-Z0-9 ]+)-----(.*?)-----END \1-----", t, _re.S)
    if not m:
        raise ValueError("no -----BEGIN ...----- / -----END ...----- block found")
    label = m.group(1)
    body = _re.sub(r"\s+", "", m.group(2))
    lines = [body[i:i + 64] for i in range(0, len(body), 64)]
    return f"-----BEGIN {label}-----\n" + "\n".join(lines) + f"\n-----END {label}-----\n"


def _decode_b64_env(value: str) -> str:
    import base64
    return base64.b64decode("".join(value.split())).decode("utf-8")


def _validated_pair(key_text: str, cert_text: str) -> tuple[str, str]:
    """Normalises both PEMs and proves they load AND belong together."""
    from cryptography import x509
    from cryptography.hazmat.primitives.serialization import load_pem_private_key

    key_pem = _normalize_pem(key_text)
    cert_pem = _normalize_pem(cert_text)
    key = load_pem_private_key(key_pem.encode(), password=None)
    cert = x509.load_pem_x509_certificate(cert_pem.encode())
    if key.public_key().public_numbers() != cert.public_key().public_numbers():
        raise ValueError("the private key does not belong to the certificate")
    return key_pem, cert_pem


def _pair_from_environment() -> tuple[str, str] | None:
    """Looks for a configured key/cert; returns None if nothing is configured."""
    candidates = []
    kb, cb = os.getenv("SIGNING_KEY_PEM_B64"), os.getenv("SIGNING_CERT_PEM_B64")
    if kb and cb:
        candidates.append(("SIGNING_KEY_PEM_B64 / SIGNING_CERT_PEM_B64", lambda: (_decode_b64_env(kb), _decode_b64_env(cb))))
    kp, cp = os.getenv("SIGNING_KEY_PEM"), os.getenv("SIGNING_CERT_PEM")
    if kp and cp:
        candidates.append(("SIGNING_KEY_PEM / SIGNING_CERT_PEM", lambda: (kp, cp)))
    sk, sc = _SECRET_FILES_DIR / "signing_key.pem", _SECRET_FILES_DIR / "signing_cert.pem"
    if sk.exists() and sc.exists():
        candidates.append(("Render secret files", lambda: (sk.read_text(), sc.read_text())))

    for source, load in candidates:
        try:
            return _validated_pair(*load())
        except Exception as exc:
            logger.error("Signing key from %s is unusable (%s: %s).", source, type(exc).__name__, exc)
    return None


def ensure_signing_identity() -> None:
    """Called once at app startup so the first report never fails for lack of a key."""
    _ensure_local_pem_files()


def _ensure_local_pem_files() -> tuple[str, str]:
    """
    Resolves to local key/cert file paths, in this order:
      1. a valid key/cert pair from env vars (…_B64 preferred) or Render secret files
      2. an existing, valid pair in CERT_DIR (local development)
      3. a freshly generated pair (with a loud warning)
    Anything configured but broken is logged with the reason and skipped, so
    report generation keeps working instead of dying with a cryptic error.
    """
    global _resolved
    if _resolved and Path(_resolved[0]).exists() and Path(_resolved[1]).exists():
        return _resolved

    configured = _pair_from_environment()
    if configured:
        CERT_DIR.mkdir(parents=True, exist_ok=True)
        KEY_PATH.write_text(configured[0])
        CERT_PATH.write_text(configured[1])
        _resolved = (str(KEY_PATH), str(CERT_PATH))
        return _resolved

    if KEY_PATH.exists() and CERT_PATH.exists():
        try:
            _validated_pair(KEY_PATH.read_text(), CERT_PATH.read_text())
            _resolved = (str(KEY_PATH), str(CERT_PATH))
            return _resolved
        except Exception as exc:
            logger.error("Existing key files in %s are unusable (%s: %s); regenerating.",
                         CERT_DIR, type(exc).__name__, exc)

    generate_signing_identity()
    logger.warning(
        "No usable signing key configured - generated a new one at %s. Fine for local "
        "development. On Render (ephemeral disk) set SIGNING_KEY_PEM_B64 / "
        "SIGNING_CERT_PEM_B64, otherwise every restart creates a new key and reports "
        "signed earlier will no longer verify as trusted.",
        CERT_DIR,
    )
    _resolved = (str(KEY_PATH), str(CERT_PATH))
    return _resolved


def sign_pdf_file(input_path: str, output_path: str) -> None:
    """Reads a plain PDF, writes a digitally-signed copy to output_path."""
    key_path, cert_path = _ensure_local_pem_files()
    signer = signers.SimpleSigner.load(key_path, cert_path, key_passphrase=None)
    if signer is None:
        # pyHanko returns None (and only logs) when the key can't be loaded.
        raise RuntimeError(
            "Could not load the report-signing key/certificate from "
            f"{CERT_DIR}. Check SIGNING_KEY_PEM_B64 / SIGNING_CERT_PEM_B64."
        )

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


# --------------------------------------------------------------------------
# Verification
#
# The check is done directly with `cryptography` rather than through pyHanko's
# validator. It is the same maths a PDF reader performs, but it has no moving
# parts: nothing here depends on pyHanko / certvalidator version quirks, and it
# can be tested without a running server.
#
#   1. ByteRange must cover the WHOLE file except the signature hole. Anything
#      appended or edited after signing is therefore detected.
#   2. SHA-256 of the covered bytes must equal the CMS messageDigest attribute.
#   3. The RSA signature over the CMS signed attributes must verify.
#   4. The signer certificate must be THIS system's certificate (so a PDF
#      signed by someone else's key is "intact" but not "trusted").
# --------------------------------------------------------------------------
import binascii as _binascii

_BYTERANGE_RE = _re.compile(rb"/ByteRange\s*\[\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*\]")

_OID_MESSAGE_DIGEST = bytes.fromhex("2a864886f70d010904")
_OID_PSS = bytes.fromhex("2a864886f70d01010a")
_DIGEST_OIDS = {
    bytes.fromhex("2b0e03021a"): "sha1",
    bytes.fromhex("608648016503040204"): "sha224",
    bytes.fromhex("608648016503040201"): "sha256",
    bytes.fromhex("608648016503040202"): "sha384",
    bytes.fromhex("608648016503040203"): "sha512",
}


def _tlv(buf: bytes, i: int):
    """Reads one DER element at offset i -> (tag, content_start, content_end)."""
    tag = buf[i]
    length = buf[i + 1]
    j = i + 2
    if length & 0x80:
        n = length & 0x7F
        length = int.from_bytes(buf[j:j + n], "big")
        j += n
    return tag, j, j + length


def _children(buf: bytes, start: int, end: int):
    """Yields (tag, content_start, content_end, element_start) for each child."""
    i = start
    while i < end:
        tag, cs, ce = _tlv(buf, i)
        yield tag, cs, ce, i
        i = ce


def _parse_cms(blob: bytes) -> dict:
    """Pulls what verification needs out of a CMS SignedData (DER)."""
    _, cs, ce = _tlv(blob, 0)                       # ContentInfo
    kids = list(_children(blob, cs, ce))
    _, sd_cs, sd_ce, _ = kids[1]                    # [0] EXPLICIT -> SignedData
    _, sdc_s, sdc_e = _tlv(blob, sd_cs)             # SignedData SEQUENCE
    certs, signer_info = [], None
    for tag, c_s, c_e, e_s in _children(blob, sdc_s, sdc_e):
        if tag == 0xA0:                             # certificates [0] IMPLICIT
            for _t, _a, _b, cert_start in _children(blob, c_s, c_e):
                certs.append(blob[cert_start:_b])
        elif tag == 0x31:                           # digestAlgs, then signerInfos (last SET)
            signer_info = (c_s, c_e)
    si_s, si_e = signer_info                        # SET OF SignerInfo
    _, info_s, info_e = _tlv(blob, si_s)            # first SignerInfo SEQUENCE
    # Fixed SignerInfo layout: version, sid, digestAlg, [signedAttrs], sigAlg, signature
    elems = list(_children(blob, info_s, info_e))
    _, oid_s, oid_e = _tlv(blob, elems[2][1])       # digestAlg -> its OID
    digest_oid = blob[oid_s:oid_e]
    signed_attrs = None
    idx = 3
    if elems[idx][0] == 0xA0:
        signed_attrs = blob[elems[idx][3]:elems[idx][2]]
        attrs_content = (elems[idx][1], elems[idx][2])
        idx += 1
    else:
        attrs_content = None
    sig_alg = elems[idx]
    _, o_s, o_e = _tlv(blob, sig_alg[1])
    sig_alg_oid = blob[o_s:o_e]
    sig_elem = elems[idx + 1]
    signature = blob[sig_elem[1]:sig_elem[2]]

    message_digest = None
    if attrs_content:
        for _t, a_s, a_e, _e in _children(blob, *attrs_content):
            _, ao_s, ao_e = _tlv(blob, a_s)
            if blob[ao_s:ao_e] == _OID_MESSAGE_DIGEST:
                set_tag, set_s, set_e = _tlv(blob, ao_e)
                _, v_s, v_e = _tlv(blob, set_s)
                message_digest = blob[v_s:v_e]

    return {
        "certs": certs,
        "digest_oid": digest_oid,
        "sig_alg_oid": sig_alg_oid,
        "signature": signature,
        # RFC 5652: signature is computed over the attributes re-tagged as SET (0x31)
        "signed_attrs_der": (b"\x31" + signed_attrs[1:]) if signed_attrs else None,
        "message_digest": message_digest,
    }


def _check_one_signature(data: bytes, match, trusted_der: bytes) -> dict:
    import hashlib
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding

    a, b, c, d = (int(x) for x in match.groups())
    result = {"intact": False, "trusted": False, "covers_whole_file": False, "reason": None}

    # The hole must be exactly the /Contents <hex> string.
    if not (0 <= a + b < c <= len(data) and data[a + b:a + b + 1] == b"<" and data[c - 1:c] == b">"):
        result["reason"] = "Malformed signature byte range."
        return result

    result["covers_whole_file"] = (a == 0 and c + d == len(data))
    covered = data[a:a + b] + data[c:c + d]
    blob = _binascii.unhexlify(data[a + b + 1:c - 1].strip())
    cms = _parse_cms(blob)

    hash_name = _DIGEST_OIDS.get(cms["digest_oid"])
    if not hash_name:
        result["reason"] = "Unsupported digest algorithm."
        return result
    hash_cls = {"sha1": hashes.SHA1, "sha224": hashes.SHA224, "sha256": hashes.SHA256,
                "sha384": hashes.SHA384, "sha512": hashes.SHA512}[hash_name]

    digest_ok = True
    if cms["message_digest"] is not None:
        digest_ok = hashlib.new(hash_name, covered).digest() == cms["message_digest"]
    signed_bytes = cms["signed_attrs_der"] if cms["signed_attrs_der"] else covered

    signer_der = None
    for cert_der in cms["certs"]:
        try:
            public_key = x509.load_der_x509_certificate(cert_der).public_key()
            if cms["sig_alg_oid"] == _OID_PSS:
                pad = padding.PSS(mgf=padding.MGF1(hash_cls()), salt_length=padding.PSS.AUTO)
            else:
                pad = padding.PKCS1v15()
            public_key.verify(cms["signature"], signed_bytes, pad, hash_cls())
            signer_der = cert_der
            break
        except Exception:
            continue

    signature_ok = signer_der is not None
    result["intact"] = bool(digest_ok and signature_ok and result["covers_whole_file"])
    result["trusted"] = bool(signer_der is not None and signer_der == trusted_der)
    if not result["intact"]:
        if not result["covers_whole_file"]:
            result["reason"] = "Content was added after the document was signed."
        elif not digest_ok:
            result["reason"] = "Document content no longer matches its signature."
        else:
            result["reason"] = "The signature itself is invalid."
    elif not result["trusted"]:
        result["reason"] = "Signed by a different key than this system's signing certificate."
    return result


def _verify_builtin(file_bytes: bytes) -> dict:
    from cryptography import x509
    from cryptography.hazmat.primitives import serialization

    _, cert_path = _ensure_local_pem_files()
    trusted_der = x509.load_pem_x509_certificate(Path(cert_path).read_bytes()).public_bytes(
        serialization.Encoding.DER
    )

    matches = list(_BYTERANGE_RE.finditer(file_bytes))
    if not matches:
        return {"signed": False, "intact": None, "trusted": None, "valid": None}

    results = [_check_one_signature(file_bytes, m, trusted_der) for m in matches]
    # Prefer the signature made by our own certificate; otherwise the last one.
    chosen = next((r for r in results if r["trusted"]), results[-1])
    ok = chosen["intact"] and chosen["trusted"]
    out = {
        "signed": True,
        "intact": chosen["intact"],
        "trusted": chosen["trusted"],
        "valid": ok,
        "bottom_line": ok,
        "engine": "builtin",
    }
    if chosen["reason"]:
        out["reason"] = chosen["reason"]
    return out


def _verify_with_pyhanko(file_bytes: bytes) -> dict:
    """Secondary path, only used if the built-in parser could not read the CMS."""
    import io

    _, cert_path = _ensure_local_pem_files()
    trust_root = load_cert_from_pemder(cert_path)
    vc = ValidationContext(trust_roots=[trust_root])
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
        "engine": "pyhanko",
    }


def verify_pdf_signature(file_bytes: bytes) -> dict:
    """
    Returns {signed, intact, trusted, valid, bottom_line, ...} for a PDF's bytes.

      signed=False  -> the PDF carries no signature at all.
      signed=None   -> something went wrong while checking; see `error`.
                       (NOT the same as unsigned - callers must not conflate them.)
      intact=False  -> the content changed after signing (the tamper signal).
      trusted=False -> the signature is not from this system's certificate.
    """
    try:
        return _verify_builtin(file_bytes)
    except Exception as builtin_exc:
        logger.warning("Built-in signature check failed (%r); trying pyHanko.", builtin_exc)
        try:
            return _verify_with_pyhanko(file_bytes)
        except Exception as hanko_exc:
            logger.exception("Signature verification failed")
            return {
                "signed": None, "intact": None, "trusted": None, "valid": None,
                "error": f"{type(builtin_exc).__name__}: {builtin_exc} | "
                         f"pyHanko: {type(hanko_exc).__name__}: {hanko_exc}",
            }


if __name__ == "__main__":
    # Optional manual (re)generation - no longer required, the app does this
    # automatically on first start if no key exists.
    generate_signing_identity()
    print(f"Generated {KEY_PATH} and {CERT_PATH}")
    print("Keep signing_key.pem secret. Do not commit either file - the certs/")
    print("folder is git-ignored.")
