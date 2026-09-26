"""Genuine OpenPGP signatures for Git fixtures without gpg-agent (ga-fsfg R3 tests).

GnuPG needs its agent, and so a Unix socket, to use a secret key; sandboxed test
runs cannot create one. This helper builds a version 4 Ed25519 key and detached
signatures in pure Python (RFC 4880 packets, EdDSA per RFC 8032). The real
`/usr/bin/gpg` then imports the public key and verifies every signature, so `%G?`
and `%GF` come from GnuPG itself.
"""

from __future__ import annotations

import base64
import hashlib
import subprocess
import time
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

ED25519_OID = bytes.fromhex("2b06010401da470f01")
EDDSA = 22
SHA256 = 8


def _mpi(value: bytes) -> bytes:
    stripped = value.lstrip(b"\0")
    bits = (len(stripped) - 1) * 8 + stripped[0].bit_length() if stripped else 0
    return bits.to_bytes(2, "big") + stripped


def _packet(tag: int, body: bytes) -> bytes:
    return bytes([0x80 | (tag << 2) | 1]) + len(body).to_bytes(2, "big") + body


def _subpacket(kind: int, data: bytes) -> bytes:
    return bytes([len(data) + 1, kind]) + data


def _crc24(data: bytes) -> int:
    crc = 0xB704CE
    for byte in data:
        crc ^= byte << 16
        for _ in range(8):
            crc <<= 1
            if crc & 0x1000000:
                crc ^= 0x1864CFB
    return crc & 0xFFFFFF


def armor(data: bytes) -> str:
    encoded = base64.b64encode(data).decode("ascii")
    lines = [encoded[index : index + 64] for index in range(0, len(encoded), 64)]
    checksum = base64.b64encode(_crc24(data).to_bytes(3, "big")).decode("ascii")
    return (
        "\n".join(
            [
                "-----BEGIN PGP SIGNATURE-----",
                "",
                *lines,
                "=" + checksum,
                "-----END PGP SIGNATURE-----",
            ]
        )
        + "\n"
    )


class SigningKey:
    """A version 4 EdDSA primary key that certifies itself and signs detached data."""

    def __init__(self, uid: str, created: int | None = None) -> None:
        self.uid = uid.encode("utf-8")
        self.created = created if created is not None else int(time.time()) - 3600
        self._private = Ed25519PrivateKey.generate()
        public = self._private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        self._body = (
            b"\x04"
            + self.created.to_bytes(4, "big")
            + bytes([EDDSA, len(ED25519_OID)])
            + ED25519_OID
            + _mpi(b"\x40" + public)
        )
        self._fingerprint = hashlib.sha1(
            b"\x99" + len(self._body).to_bytes(2, "big") + self._body
        ).digest()

    @property
    def fingerprint(self) -> str:
        """The fingerprint as git reports it in %GF."""

        return self._fingerprint.hex().upper()

    def _signature(self, kind: int, prefix: bytes, created: int, extra: bytes = b"") -> bytes:
        hashed = (
            _subpacket(2, created.to_bytes(4, "big"))
            + _subpacket(33, b"\x04" + self._fingerprint)
            + extra
        )
        head = bytes([4, kind, EDDSA, SHA256]) + len(hashed).to_bytes(2, "big") + hashed
        trailer = b"\x04\xff" + len(head).to_bytes(4, "big")
        digest = hashlib.sha256(prefix + head + trailer).digest()
        signed = self._private.sign(digest)
        unhashed = _subpacket(16, self._fingerprint[-8:])
        body = head + len(unhashed).to_bytes(2, "big") + unhashed + digest[:2]
        return _packet(2, body + _mpi(signed[:32]) + _mpi(signed[32:]))

    def public_key(self) -> bytes:
        """The transferable public key: key, user id and positive self-certification."""

        key_prefix = b"\x99" + len(self._body).to_bytes(2, "big") + self._body
        uid_prefix = b"\xb4" + len(self.uid).to_bytes(4, "big") + self.uid
        certification = self._signature(
            0x13, key_prefix + uid_prefix, self.created, _subpacket(27, b"\x03")
        )
        return _packet(6, self._body) + _packet(13, self.uid) + certification

    def sign(self, data: bytes) -> str:
        """An armored detached binary-document signature over `data`."""

        return armor(self._signature(0x00, data, int(time.time()) - 60))


def install_public_key(home: Path, key: SigningKey, *, trusted: bool = True) -> None:
    """Import the key into `<home>/.gnupg`; `trusted` sets ultimate ownertrust."""

    gnupg = home / ".gnupg"
    gnupg.mkdir(parents=True, exist_ok=True)
    gnupg.chmod(0o700)
    keyfile = gnupg / f"{key.fingerprint}.pgp"
    keyfile.write_bytes(key.public_key())
    env = {"HOME": str(home), "PATH": "/usr/bin:/bin"}
    subprocess.run(
        ["/usr/bin/gpg", "--batch", "--no-autostart", "--import", str(keyfile)],
        env=env,
        capture_output=True,
        check=False,
    )
    listing = subprocess.run(
        ["/usr/bin/gpg", "--batch", "--with-colons", "--list-keys", key.fingerprint],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert key.fingerprint in listing.stdout, listing.stderr
    if trusted:
        result = subprocess.run(
            ["/usr/bin/gpg", "--batch", "--import-ownertrust"],
            env=env,
            input=f"{key.fingerprint}:6:\n",
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr


def signed_commit_object(unsigned: bytes, signature: str) -> bytes:
    """Insert a `gpgsig` header into a raw commit object, exactly as git writes it."""

    headers, separator, message = unsigned.partition(b"\n\n")
    assert separator, "a commit object has a header block"
    lines = signature.rstrip("\n").split("\n")
    gpgsig = ("gpgsig " + "\n ".join(lines)).encode("utf-8")
    return headers + b"\n" + gpgsig + b"\n\n" + message
