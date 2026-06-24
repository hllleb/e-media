"""Prime generation using Miller-Rabin probabilistic primality test."""

from __future__ import annotations

import secrets


def _miller_rabin(n: int, rounds: int = 40) -> bool:
    """Return True if *n* is probably prime."""
    if n < 2:
        return False
    small_primes = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for p in small_primes:
        if n == p:
            return True
        if n % p == 0:
            return False

    # Write n-1 as d * 2^s with d odd.
    d = n - 1
    s = 0
    while d % 2 == 0:
        d //= 2
        s += 1

    for _ in range(rounds):
        a = secrets.randbelow(n - 3) + 2
        x = pow(a, d, n)
        if x == 1 or x == n - 1:
            continue
        for _ in range(s - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True


def generate_prime(bits: int) -> int:
    """Generate a random probable prime with the given bit length."""
    if bits < 2:
        raise ValueError("Prime bit length must be at least 2.")

    while True:
        candidate = secrets.randbits(bits)
        candidate |= 1 << (bits - 1)  # ensure exact bit length
        candidate |= 1  # ensure odd
        if _miller_rabin(candidate):
            return candidate


def is_probable_prime(n: int) -> bool:
    """Public wrapper for Miller-Rabin."""
    return _miller_rabin(n)
