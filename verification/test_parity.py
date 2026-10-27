#!/usr/bin/env python3
"""verify.py ↔ verify.ts EŞLİK sınaması.

    python3 test_parity.py        # Node 22.6+ gerekir (verify.ts tip-soyma ile koşar)

İki uygulama aynı kayıtta aynı hükmü vermek ZORUNDA (KLM-Spec §8.4). Her
doğrulayıcının `--self-test`i yalnız kendini koşar; iki dilin AYRIŞMASINI
göremez. 2026-09-26'da tam bu sınıftan üç kusur bulundu, hiçbiri öz-sınamada
görünmüyordu:

  · `"algorithm": []` / `{}` — Python "yanlış-değer" sayıp eski biçimle
    hash'liyordu (FAIL, çıkış 2), JS tanınmayan beyan sayıyordu (çıkış 3);
  · `""`, `0`, `false` — Python FAIL/2, JS PASS/0;
  · eşi olmayan vekil (`"\\ud800x"`) — verify.py UnicodeEncodeError/çıkış 1,
    verify.ts çıkış 3.

Bu betik örnek kaydın kopyalarını GEÇİCİ bir dizinde üretir (bu klasöre
yazmaz), iki doğrulayıcıyı `--json` ile koşar ve çıkış kodunu,
`content_integrity` durumunu ve — iddia edilen yerde — bayt bayt aynı çıktıyı
denetler. Önce iki öz-sınamayı da koşar. Çıkış 0: hepsi tuttu · 1: en az bir
vaka tutmadı.

Bilinçli olarak SINANMAYANLAR (kanıtlı bilinen ayrışmalar, bu betiğin konusu
değil):
  · kurcalanmış kayıtta FAIL ayrıntısı — verify.ts tam değerli sayı ipucunu
    ekler; hüküm ve çıkış kodu yine karşılaştırılır.
  · beyansız / `null` beyan — eski `sha256` biçimi dile bağlıdır (Python
    `1.0`, JS `1`; README "En ağır bulgu"). Yalnız eski yola gidildiği
    (`unsupported_algorithm` DEĞİL) sınanır.
"""
from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLE = os.path.join(HERE, "sample", "receipt.json")
PUBKEY = os.path.join(HERE, "sample", "pubkey.txt")
UNSUPPORTED = "unsupported_algorithm"


def _node_cmd() -> list[str]:
    """Node 23.6+ tipleri kendiliğinden soyar; 22.6–23.5 bayrak ister."""
    out = subprocess.run(["node", "--version"], capture_output=True, text=True).stdout
    major, minor = (int(x) for x in out.strip().lstrip("v").split(".")[:2])
    flag = [] if (major, minor) >= (23, 6) else ["--experimental-strip-types"]
    return ["node", *flag, os.path.join(HERE, "verify.ts")]


def _with_alg(base: dict, value, drop: bool = False) -> dict:
    r = copy.deepcopy(base)
    ver = r["meta"]["verification"]
    if drop:
        ver.pop("algorithm", None)
    else:
        ver["algorithm"] = value
    return r


def _tamper(base: dict) -> dict:
    r = copy.deepcopy(base)
    r["answer"] = r["answer"] + "!"
    return r


def _cases(base: dict) -> list[tuple[str, dict, dict]]:
    """(ad, kayıt, beklenen). beklenen: exit, status, prefix, identical, legacy."""
    unsupported = {"exit": 3, "status": "NOT MEASURED", "prefix": UNSUPPORTED,
                   "identical": True}
    legacy = {"legacy": True}
    tampered9 = _tamper(base)
    tampered9["meta"]["verification"]["algorithm"] = "sha256-canonical/9"
    return [
        ("intact sample", base,
         {"exit": 0, "status": "PASS", "identical": True}),
        ("one value tampered", _tamper(base),
         {"exit": 2, "status": "FAIL"}),
        ('algorithm "sha256-canonical/9"', _with_alg(base, "sha256-canonical/9"), unsupported),
        ('algorithm ""', _with_alg(base, ""), unsupported),
        ("algorithm 0", _with_alg(base, 0), unsupported),
        ("algorithm false", _with_alg(base, False), unsupported),
        ("algorithm []", _with_alg(base, []), unsupported),
        ("algorithm {}", _with_alg(base, {}), unsupported),
        ("algorithm lone surrogate", _with_alg(base, "\ud800x"), unsupported),
        ("algorithm ş + emoji + lone surrogate",
         _with_alg(base, "ş\U0001F600\udc00"), unsupported),
        ("tampered + unknown algorithm", tampered9, unsupported),
        ("algorithm key absent", _with_alg(base, None, drop=True), legacy),
        ("algorithm null", _with_alg(base, None), legacy),
    ]


def _run(cmd: list[str], path: str) -> tuple[int, dict | None, bytes, str]:
    pr = subprocess.run(cmd + [path, "--pubkey", PUBKEY, "--json"], capture_output=True)
    try:
        return pr.returncode, json.loads(pr.stdout.decode("utf-8")), pr.stdout, ""
    except ValueError:
        err = pr.stderr.decode("utf-8", "replace").strip().splitlines()
        return pr.returncode, None, pr.stdout, (err[-1] if err else "no output")


def _check(expect: dict, py, ts) -> list[str]:
    problems = []
    for lang, (code, out, _, err) in (("py", py), ("ts", ts)):
        if out is None:
            problems.append(f"{lang} crashed (exit {code}): {err}")
            continue
        ci = out["checks"]["content_integrity"]
        if "exit" in expect and code != expect["exit"]:
            problems.append(f"{lang} exit {code}, expected {expect['exit']}")
        if "status" in expect and ci["status"] != expect["status"]:
            problems.append(f"{lang} content_integrity {ci['status']}, "
                            f"expected {expect['status']}")
        if "prefix" in expect and not ci["detail"].startswith(expect["prefix"]):
            problems.append(f"{lang} detail does not start with {expect['prefix']}")
        if expect.get("legacy") and ci["detail"].startswith(UNSUPPORTED):
            problems.append(f"{lang} treated an undeclared algorithm as declared")
    if not problems and expect.get("identical") and py[2] != ts[2]:
        problems.append("--json output differs between verify.py and verify.ts")
    return problems


def main() -> int:
    py_cmd = [sys.executable, os.path.join(HERE, "verify.py")]
    ts_cmd = _node_cmd()
    failed = []

    print("\n── SELF-TESTS ──")
    for lang, cmd in (("verify.py", py_cmd), ("verify.ts", ts_cmd)):
        code = subprocess.run(cmd + [SAMPLE, "--pubkey", PUBKEY, "--self-test"],
                              capture_output=True).returncode
        print(f"  {'✓' if code == 0 else '✗'} {lang} --self-test  exit {code}")
        if code != 0:
            failed.append(f"{lang} --self-test")

    print("\n── PARITY: verify.py vs verify.ts on variants of the sample ──")
    with open(SAMPLE, encoding="utf-8") as fh:
        base = json.load(fh)
    with tempfile.TemporaryDirectory(prefix="nage-verify-parity-") as tmp:
        for i, (name, record, expect) in enumerate(_cases(base)):
            path = os.path.join(tmp, f"case{i:02d}.json")
            with open(path, "w", encoding="utf-8") as fh:
                # ensure_ascii=True: eşi olmayan vekil `\ud800` kaçışıyla
                # yazılır — geçerli JSON, iki dilde de aynı dizeye açılır.
                json.dump(record, fh, ensure_ascii=True, indent=2)
            py, ts = _run(py_cmd, path), _run(ts_cmd, path)
            problems = _check(expect, py, ts)
            note = ("  (legacy path; verdicts not compared)"
                    if expect.get("legacy") else "")
            print(f"  {'✓' if not problems else '✗'} {name:<38} "
                  f"py exit {py[0]} · ts exit {ts[0]}{note}")
            for p in problems:
                print(f"      {p}")
            if problems:
                failed.append(name)

    if failed:
        print(f"\n  PARITY BROKEN — {len(failed)} case(s): {failed}\n")
        return 1
    print("\n  every case met its expectation ✓\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
