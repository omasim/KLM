"""Pure-Python Ed25519 (RFC 8032) — stdlib-only reference implementation.

Exists so the KLM conformance tooling stays dependency-free: any third
party can verify a signed attestation record with nothing but Python.

HONEST SCOPE NOTE: this is the classic reference construction — correct
but slow and NOT constant-time. Verification of public data is safe;
production *signing* should use a hardened library (`cryptography`,
libsodium — seds-klm already does). sign_attestation.py auto-prefers
`cryptography` when installed and falls back to this module.
"""

from __future__ import annotations

import hashlib

_p = 2**255 - 19
_q = 2**252 + 27742317777372353535851937790883648493


def _H(m: bytes) -> bytes:
    return hashlib.sha512(m).digest()


def _inv(x: int) -> int:
    return pow(x, _p - 2, _p)


_d = (-121665 * _inv(121666)) % _p
_I = pow(2, (_p - 1) // 4, _p)


def _xrecover(y: int) -> int:
    xx = (y * y - 1) * _inv(_d * y * y + 1)
    x = pow(xx, (_p + 3) // 8, _p)
    if (x * x - xx) % _p != 0:
        x = (x * _I) % _p
    if x % 2 != 0:
        x = _p - x
    return x


_By = (4 * _inv(5)) % _p
_Bx = _xrecover(_By)
_B = (_Bx, _By)


def _edwards_add(P: tuple[int, int], Q: tuple[int, int]) -> tuple[int, int]:
    x1, y1 = P
    x2, y2 = Q
    x3 = (x1 * y2 + x2 * y1) * _inv(1 + _d * x1 * x2 * y1 * y2)
    y3 = (y1 * y2 + x1 * x2) * _inv(1 - _d * x1 * x2 * y1 * y2)
    return (x3 % _p, y3 % _p)


def _scalarmult(P: tuple[int, int], e: int) -> tuple[int, int]:
    Q = (0, 1)
    while e > 0:
        if e & 1:
            Q = _edwards_add(Q, P)
        P = _edwards_add(P, P)
        e >>= 1
    return Q


def _encodeint(y: int) -> bytes:
    return y.to_bytes(32, "little")


def _encodepoint(P: tuple[int, int]) -> bytes:
    x, y = P
    return ((y | ((x & 1) << 255)).to_bytes(32, "little"))


def _decodepoint(s: bytes) -> tuple[int, int]:
    v = int.from_bytes(s, "little")
    y = v & ((1 << 255) - 1)
    x = _xrecover(y)
    if x & 1 != (v >> 255) & 1:
        x = _p - x
    P = (x, y)
    # on-curve check: -x^2 + y^2 = 1 + d x^2 y^2
    if (-x * x + y * y - 1 - _d * x * x * y * y) % _p != 0:
        raise ValueError("point not on curve")
    return P


def _clamp(h: bytes) -> int:
    a = int.from_bytes(h[:32], "little")
    a &= (1 << 254) - 8
    a |= 1 << 254
    return a


def publickey(seed: bytes) -> bytes:
    """32-byte seed → 32-byte public key."""
    a = _clamp(_H(seed))
    return _encodepoint(_scalarmult(_B, a))


def sign(msg: bytes, seed: bytes, pub: bytes) -> bytes:
    h = _H(seed)
    a = _clamp(h)
    r = int.from_bytes(_H(h[32:] + msg), "little") % _q
    R = _encodepoint(_scalarmult(_B, r))
    k = int.from_bytes(_H(R + pub + msg), "little") % _q
    S = (r + k * a) % _q
    return R + _encodeint(S)


def verify(msg: bytes, sig: bytes, pub: bytes) -> bool:
    if len(sig) != 64 or len(pub) != 32:
        return False
    try:
        R = _decodepoint(sig[:32])
        A = _decodepoint(pub)
    except ValueError:
        return False
    S = int.from_bytes(sig[32:], "little")
    if S >= _q:
        return False
    k = int.from_bytes(_H(sig[:32] + pub + msg), "little") % _q
    left = _scalarmult(_B, S)
    right = _edwards_add(R, _scalarmult(A, k))
    return left == right
