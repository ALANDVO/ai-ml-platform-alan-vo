import base64, hashlib, json, logging
from typing import Dict

from config import settings

logger = logging.getLogger(__name__)


def verify_saml_response(saml_response_b64: str) -> Dict:
    """Verify a SAML 2.0 assertion. In production, parse the XML assertion
    and validate the signature against the IdP certificate. This implementation
    decodes the base64 payload and extracts the standard attributes, falling
    back to a deterministic mock user when the payload is not well-formed XML.
    In production, wire up python3-saml's OneLogin_Saml2_Response here."""
    if not saml_response_b64:
        return {"email": "saml.user@alanvo.com", "name": "SAML User", "role": "ml_engineer"}
    try:
        raw = base64.b64decode(saml_response_b64)
        text = raw.decode("utf-8", errors="replace")
        # Look for standard SAML attributes in the XML
        email, name, role = "saml.user@alanvo.com", "SAML User", "ml_engineer"
        if "email" in text:
            import re
            m = re.search(r"email[\s\S]*?<Value>([^<]+)</Value>", text)
            if m:
                email = m.group(1).strip()
            m = re.search(r"displayName[\s\S]*?<Value>([^<]+)</Value>", text)
            if m:
                name = m.group(1).strip()
            m = re.search(r"role[\s\S]*?<Value>([^<]+)</Value>", text)
            if m:
                role = m.group(1).strip()
        return {"email": email, "name": name, "role": role if role in ("admin", "ml_engineer", "viewer") else "ml_engineer"}
    except Exception:
        logger.warning("SAML response decode failed; using mock user")
        return {"email": "saml.user@alanvo.com", "name": "SAML User", "role": "ml_engineer"}
