"""RSA key generation and JSON persistence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .padding import raw_plaintext_block_size
from .primes import generate_prime

DEFAULT_PUBLIC_EXPONENT = 65537


@dataclass(frozen=True)
class RSAKeyPair:
    """RSA public/private key material."""

    n: int
    e: int
    d: int
    p: int | None = None
    q: int | None = None
    bits: int = 2048

    @property
    def modulus_bytes(self) -> int:
        return (self.n.bit_length() + 7) // 8

    @property
    def plaintext_block_size(self) -> int:
        return raw_plaintext_block_size(self.n.bit_length())

    @property
    def max_plaintext_size(self) -> int:
        return self.plaintext_block_size

    def to_dict(self) -> dict:
        data = {
            "n": hex(self.n),
            "e": hex(self.e),
            "d": hex(self.d),
            "bits": self.bits,
        }
        if self.p is not None:
            data["p"] = hex(self.p)
        if self.q is not None:
            data["q"] = hex(self.q)
        return data

    @classmethod
    def from_dict(cls, data: dict) -> RSAKeyPair:
        return cls(
            n=int(data["n"], 16),
            e=int(data["e"], 16),
            d=int(data["d"], 16),
            p=int(data["p"], 16) if "p" in data else None,
            q=int(data["q"], 16) if "q" in data else None,
            bits=int(data.get("bits", 2048)),
        )


def generate_keypair(bits: int = 2048, e: int = DEFAULT_PUBLIC_EXPONENT) -> RSAKeyPair:
    """Generate a new RSA key pair with *bits*-bit modulus."""
    if bits < 512 or bits % 2 != 0:
        raise ValueError("Key size must be an even integer >= 512.")

    half = bits // 2
    while True:
        p = generate_prime(half)
        q = generate_prime(half)
        if p == q:
            continue
        n = p * q
        if n.bit_length() != bits:
            continue
        phi = (p - 1) * (q - 1)
        if phi % e == 0:
            continue
        d = pow(e, -1, phi)
        return RSAKeyPair(n=n, e=e, d=d, p=p, q=q, bits=bits)


def save_keypair(key: RSAKeyPair, path: str | Path) -> None:
    """Write key material to a JSON file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(key.to_dict(), f, indent=2)


def load_keypair(path: str | Path) -> RSAKeyPair:
    """Load key material from a JSON file."""
    with Path(path).open(encoding="utf-8") as f:
        return RSAKeyPair.from_dict(json.load(f))
