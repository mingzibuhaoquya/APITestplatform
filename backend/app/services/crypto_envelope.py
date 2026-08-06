import base64
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


FIXED_PUBLIC_KEY_PATH = Path("keys/request_public.pem")
FIXED_PRIVATE_KEY_PATH = Path("keys/response_private.pem")


class CryptoEnvelopeError(Exception):
    pass


def default_config() -> dict[str, Any]:
    return {
        "mode": "none",
        "encrypt_request": False,
        "decrypt_response": False,
        "client_header": "appKey",
        "sm3_signature": False,
    }


def normalize_config(value: dict[str, Any] | None) -> dict[str, Any]:
    config = {**default_config(), **(value or {})}
    if config["mode"] != "rsa_aes_sm3":
        config["mode"] = "none"
    config["encrypt_request"] = bool(config["encrypt_request"])
    config["decrypt_response"] = bool(config["decrypt_response"])
    if config["mode"] == "none":
        config["encrypt_request"] = False
        config["decrypt_response"] = False
    config["client_header"] = str(config.get("client_header") or "appKey").strip() or "appKey"
    config["sm3_signature"] = bool(config.get("sm3_signature"))
    return config


def public_config(value: dict[str, Any] | None) -> dict[str, Any]:
    config = normalize_config(value)
    return {
        "mode": config["mode"],
        "encrypt_request": config["encrypt_request"],
        "decrypt_response": config["decrypt_response"],
        "client_header": config["client_header"],
        "sm3_signature": config["sm3_signature"],
        "public_key_configured": FIXED_PUBLIC_KEY_PATH.is_file(),
        "private_key_configured": FIXED_PRIVATE_KEY_PATH.is_file(),
    }


def _fixed_key_path(path: Path, key_label: str) -> Path:
    if not path.is_file():
        raise CryptoEnvelopeError(f"Fixed {key_label} key is unavailable on the server")
    return path


def _header_value(headers: dict[str, Any], name: str) -> str:
    for key, value in headers.items():
        if key.lower() == name.lower():
            return str(value or "")
    return ""


def _sm3(data: bytes) -> bytes:
    try:
        return hashlib.new("sm3", data).digest()
    except ValueError as exc:
        raise CryptoEnvelopeError("SM3 is unavailable in this runtime") from exc


def sm3_hex(text: str) -> str:
    return _sm3(text.encode("utf-8")).hex().upper()


def append_sm3_signature(body: Any, body_format: str) -> tuple[str, dict[str, Any]]:
    if body_format != "xml":
        raise CryptoEnvelopeError("SM3尾部签名第一版仅支持 XML 请求体")
    if body in ({}, "", None):
        raise CryptoEnvelopeError("SM3尾部签名需要非空请求体")
    text = str(body)
    signature = sm3_hex(text)
    return text + signature, {
        "enabled": True,
        "placement": "body_tail",
        "algorithm": "SM3",
        "format": "HEX_UPPER",
        "separator": "",
        "value": signature,
        "source_length": len(text),
    }


def encrypt_body(body: Any, headers: dict[str, Any], config: dict[str, Any]) -> dict[str, str]:
    normalized = normalize_config(config)
    client = _header_value(headers, normalized["client_header"])
    if not client:
        raise CryptoEnvelopeError(f"Missing client header: {normalized['client_header']}")
    try:
        public_key = serialization.load_pem_public_key(_fixed_key_path(FIXED_PUBLIC_KEY_PATH, "public").read_bytes())
    except (TypeError, ValueError) as exc:
        raise CryptoEnvelopeError("Unable to load request encryption public key") from exc
    if not isinstance(public_key, rsa.RSAPublicKey):
        raise CryptoEnvelopeError("Request encryption key is not RSA")
    plain = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    aes_key, iv = os.urandom(32), os.urandom(12)
    cipher = AESGCM(aes_key).encrypt(iv, plain, None)
    encrypted_key = public_key.encrypt(aes_key, padding.PKCS1v15())
    return {
        "encryptedKey": base64.b64encode(encrypted_key).decode("ascii"),
        "cipher": base64.b64encode(cipher).decode("ascii"),
        "iv": base64.b64encode(iv).decode("ascii"),
        "digest": base64.b64encode(_sm3(plain)).decode("ascii"),
        "client": client,
    }


def decrypt_body(envelope: Any, config: dict[str, Any]) -> tuple[str, Any]:
    if not isinstance(envelope, dict):
        raise CryptoEnvelopeError("Encrypted response must be a JSON object")
    try:
        private_key = serialization.load_pem_private_key(_fixed_key_path(FIXED_PRIVATE_KEY_PATH, "private").read_bytes(), password=None)
        aes_key = private_key.decrypt(base64.b64decode(envelope["encryptedKey"]), padding.PKCS1v15())
        plain = AESGCM(aes_key).decrypt(base64.b64decode(envelope["iv"]), base64.b64decode(envelope["cipher"]), None)
    except (KeyError, TypeError, ValueError) as exc:
        raise CryptoEnvelopeError("Unable to decrypt response envelope") from exc
    expected = envelope.get("digest")
    actual = base64.b64encode(_sm3(plain)).decode("ascii")
    if actual != expected:
        raise CryptoEnvelopeError("Response SM3 digest verification failed")
    text = plain.decode("utf-8")
    try:
        return text, json.loads(text)
    except json.JSONDecodeError:
        return text, text
