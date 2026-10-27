/**
 * Nage tasdik kaydı — BAĞIMSIZ doğrulayıcı, İKİNCİ UYGULAMA.
 *
 *   npx tsx verify.ts sample/receipt.json --pubkey sample/pubkey.txt
 *   npx tsx verify.ts sample/receipt.json --self-test
 *
 * ─────────────────────────────────────────────────────────────────────
 * NEDEN İKİNCİ BİR UYGULAMA
 * ─────────────────────────────────────────────────────────────────────
 * KLM-Spec §8.4 (iki-uygulama şartı): aynı doğrulayıcı hem platform
 * üreticisinin hem bağımsız RILL üreticisinin kaydını geçirmeli. Tek bir
 * doğrulayıcı, kaydın "doğrulanabilir" olduğunu değil, YALNIZ O KODUN
 * kabul ettiğini gösterir.
 *
 * `verify.py` ile bu dosya AYRI YAZILDI ve aynı kayıt üzerinde aynı
 * hükmü vermek ZORUNDA. Ayrışırlarsa sorun kayıtta değil ŞARTNAMEDEDİR:
 * kanonik biçim, null sözleşmesi ya da imza kapsamı yeterince
 * belirtilmemiş demektir. Python sürümü yazılırken tam olarak bu oldu —
 * kanonik biçimin iki farklı hâli bulundu ve ancak yazılı hâle
 * getirildikten sonra ikisi uyuştu.
 *
 * Node 18+ yeterli; harici bağımlılık yok. Ed25519 `node:crypto` ile.
 */
import { createHash, createPublicKey, verify as edVerify } from "node:crypto";
import { readFileSync } from "node:fs";

type Tier = "unconditional" | "conditional";
type Status = "PASS" | "FAIL" | "NOT MEASURED";
interface Check { status: Status; tier: Tier; detail: string }

const OK: Status = "PASS", FAIL: Status = "FAIL", UNMEASURED: Status = "NOT MEASURED";

/** Hash'in DIŞINDA kalan alanlar — kendine referans olurlardı. */
const STRIPPED = ["verification", "signature", "record_ref"] as const;

/**
 * Makbuz kanonik biçimi — `verification/README.md`'deki tanımın birebir
 * karşılığı. Üç ayrıntı tahmin edilemez, o yüzden burada da açık:
 *   1. anahtarlar sıralı, ayraçlar boşluksuz
 *   2. ASCII kaçışlı ("ç" → ç) — üretenin biçimi
 *   3. boşalan `meta` TAMAMEN düşer ({} ile yokluk aynı gövde değildir)
 */
function canonical(value: unknown): string {
  if (value === null || typeof value !== "object") {
    return escapeNonAscii(JSON.stringify(value) ?? "null");
  }
  if (Array.isArray(value)) {
    return "[" + value.map(canonical).join(",") + "]";
  }
  const keys = Object.keys(value as object).sort();
  return "{" + keys
    .map((k) => escapeNonAscii(JSON.stringify(k)) + ":" +
                canonical((value as Record<string, unknown>)[k]))
    .join(",") + "}";
}

/** JSON.stringify ham UTF-8 yazar; üreten ASCII kaçışlı yazıyor. */
function escapeNonAscii(s: string): string {
  // U+007F (DEL) de kaçışlanır: Python json.dumps(ensure_ascii=True) U+0020–U+007E dışını
  // kaçışlar; eski aralık U+0080'den başladığı için DEL'li makbuzlar FAIL oluyordu (v3 denetimi 2026-09-25).
  return s.replace(/[\u007f-\uffff]/g, (c) =>
    "\\u" + c.charCodeAt(0).toString(16).padStart(4, "0"));
}

/** `sha256-canonical/2` — sayılar dilden bağımsız (tam değerli float `1`). */
function canonicalV2(value: unknown): string {
  if (value === null) return "null";
  if (typeof value === "boolean") return value ? "true" : "false";
  if (typeof value === "number") {
    if (!Number.isFinite(value)) throw new Error(`non-canonical number: ${value}`);
    return Number.isInteger(value) && Math.abs(value) < 1e16
      ? String(value) : String(value);
  }
  if (typeof value === "string") return escapeNonAscii(JSON.stringify(value));
  if (Array.isArray(value)) return "[" + value.map(canonicalV2).join(",") + "]";
  const o = value as Record<string, unknown>;
  return "{" + Object.keys(o).sort()
    .map((k) => escapeNonAscii(JSON.stringify(k)) + ":" + canonicalV2(o[k]))
    .join(",") + "}";
}

/**
 * `sha256-canonical/3` — sayılar ECMAScript Number::toString (`String(x)`),
 * anahtarlar `.sort()` (UTF-16 kod birimi). JS tarafında bu, `canonicalV2`nin
 * TA KENDİSİDİR: burada sayıyı dilin kendisi yazıyor. Ayrı ad, kaydın beyan
 * ettiği algoritmayla dallanmak için.
 *
 * Neden v3 (2026-09-25): v2'yi üreten Python `repr`i |x| < 1e-4 için üslü
 * yazar ("5e-05"), JS `String()` ondalık ("0.00005"). v2'nin "[0,1]
 * aralığında aynı" beyanı bu aralıkta yanlıştı; böyle bir sayı taşıyan v2
 * makbuzu BU doğrulayıcıda tutmaz (kayıt bozulmadan). v3'te üretici
 * (platform receipt._canonical_v3) ECMAScript biçimini yazar.
 */
const canonicalV3 = canonicalV2;

/** Hangi kanonik biçim? KAYIT SÖYLER. Beyan yoksa eski `sha256`. Dönen
 *  değer kayıttan geldiği gibidir; dize olması garanti değil.
 *
 *  Beyan VARLIKLA belirlenir, doğrulukla değil: `""`, `0`, `false`, `[]`,
 *  `{}` da beyandır (ve tanınmaz). Yalnız anahtarın yokluğu ya da `null`
 *  beyansızdır. `src?.algorithm` doğruluk sınamasıydı; "yanlış-değer" kümesi
 *  dillere göre değişir (`[]`/`{}` Python'da yanlış, JS'te doğru) ve iki
 *  uygulama aynı kayıtta ayrışıyordu (2026-09-26 bulgusu). */
function algorithmOf(record: any): unknown {
  for (const src of [record.meta?.verification, record.verification]) {
    if (src !== null && typeof src === "object" && src.algorithm != null) return src.algorithm;
  }
  return "sha256";
}

/**
 * Bu doğrulayıcının uyguladığı kanonik biçimler — KAPALI liste; verify.py
 * `_KNOWN_ALGORITHMS` ile birebir. Beyan YOKSA eski yol; beyan VAR ama
 * listede değilse bütünlük ÖLÇÜLMEDİ (`unsupported_algorithm`). Ölçülen
 * (2026-09-26, örnek kayıt `sha256-canonical/9` beyanıyla), bu değişiklikten
 * önce: bu dosya PASS/çıkış 0 — hüküm DOĞRUYDU (burada eski yedek biçim v2
 * ile aynı baytları üretir; sayıyı ikisi de `String(x)` yazar), yanlış olan
 * yalnız ayrıntıdaki `[sha256-canonical/9]` etiketiydi; verify.py ise
 * FAIL/çıkış 2 — sağlam makbuza SAHTE kurcalama. Bilinen biçimleri yedek
 * olarak DENEMEMEK bir tercihtir, bilinemezlik değil: tutmayan bir yedek
 * kurcalama göstermez ve tutup tutmadığı dile göre değişir.
 */
const KNOWN_ALGORITHMS = ["sha256", "sha256-canonical/2", "sha256-canonical/3"] as const;

function bodyForHash(record: Record<string, any>): Record<string, any> {
  const body: Record<string, any> = JSON.parse(JSON.stringify(record));
  for (const k of STRIPPED) delete body[k];
  if (body.meta && typeof body.meta === "object") {
    delete body.meta.verification;
    if (Object.keys(body.meta).length === 0) delete body.meta;
  }
  return body;
}

function claimedSignature(record: Record<string, any>): string | null {
  for (const src of [record.meta?.verification, record.verification]) {
    if (src && typeof src === "object" && src.signature) return src.signature;
  }
  return record.record_ref?.record_hash ?? null;
}

function* walk(obj: any, path = ""): Generator<[string, any]> {
  if (obj !== null && typeof obj === "object") {
    if (Array.isArray(obj)) {
      for (let i = 0; i < obj.length; i++) yield* walk(obj[i], `${path}[${i}]`);
    } else {
      for (const k of Object.keys(obj)) yield* walk(obj[k], path ? `${path}.${k}` : k);
    }
  } else {
    yield [path, obj];
  }
}

function at(root: any, path: string): any {
  let node = root;
  for (const raw of path.split(".").filter(Boolean)) {
    const m = raw.match(/^([^\[]*)((?:\[\d+\])*)$/);
    if (!m) return undefined;
    if (m[1]) node = node?.[m[1]];
    for (const idx of m[2].match(/\d+/g) ?? []) node = node?.[Number(idx)];
    if (node === undefined || node === null) return node;
  }
  return node;
}

// ───────────────────────────────────────────────────────── kontroller
/**
 * Tam sayı değerli float'ları bulur — bilinen DİLLER-ARASI kanonikleştirme
 * boşluğunun tetikleyicisi.
 *
 * Python `json.dumps` bir float'ı `1.0` yazar; JavaScript `JSON.stringify`
 * aynı değeri `1` yazar. JS'te float/int ayrımı YOKTUR. Yani bir skor tam
 * olarak 0 ya da 1 olduğunda iki uygulama FARKLI kanonik gövde üretir ve
 * bütünlük hash'i tutmaz — kayıtta hiçbir bozulma olmadan.
 *
 * Bu, KLM-5'in "üçüncü tarafça doğrulanabilir" iddiasını bütün bir kayıt
 * sınıfı için geçersiz kılar, ve ancak Python DIŞINDA biri denediğinde
 * görünür. İki-uygulama şartının (KLM-Spec §8.4) var olma sebebi tam bu.
 */
function integralFloats(record: any): string[] {
  const hits: string[] = [];
  for (const [path, val] of walk(record)) {
    if (typeof val === "number" && Number.isInteger(val) && !/\[\d+\]$/.test(path)) {
      hits.push(path);
    }
  }
  return hits;
}

function checkIntegrity(record: any): Check {
  const claimed = claimedSignature(record);
  const alg = algorithmOf(record);
  if (!(KNOWN_ALGORITHMS as readonly unknown[]).includes(alg)) {
    const shown = typeof alg === "string" ? JSON.stringify(alg) : "a non-string value";
    return { status: UNMEASURED, tier: "unconditional",
             detail: `unsupported_algorithm: record declares ${shown}; this ` +
                     `verifier implements ${KNOWN_ALGORITHMS.join(", ")} — ` +
                     "not hashed, and no known form is tried in its place, " +
                     "so no integrity verdict either way" };
  }
  const body = bodyForHash(record);
  const blob = alg === "sha256-canonical/3" ? canonicalV3(body)
    : alg === "sha256-canonical/2" ? canonicalV2(body) : canonical(body);
  const computed = "sha256:" + createHash("sha256").update(blob, "utf8").digest("hex");
  if (!claimed) {
    return { status: UNMEASURED, tier: "unconditional",
             detail: "record carries no signature / record_hash" };
  }
  if (computed === claimed) {
    return { status: OK, tier: "unconditional",
             detail: `[${alg}] computed ${computed.slice(0, 23)}… · declared ${claimed.slice(0, 23)}…` };
  }
  // Başarısızlığın BİLİNEN bir sebebi varsa söylenir. "Tutmadı" demek,
  // doğrulayanı kayıtta kurcalama aramaya gönderir — oysa sebep şartnamede.
  const suspects = integralFloats(record);
  const known = suspects.length
    ? ` · POSSIBLE KNOWN CAUSE: ${suspects.length} integral-valued number(s) ` +
      `(${suspects.slice(0, 3).join(", ")}). Python writes these as \`1.0\`, ` +
      `JavaScript as \`1\` → different canonical body. JSON does NOT record ` +
      `which of them was a float, so these are candidates; but the cause is ` +
      `not corruption, it is an UNDERSPECIFIED canonical NUMBER format.`
    : "";
  return { status: FAIL, tier: "unconditional",
           detail: `computed ${computed.slice(0, 23)}… · declared ${claimed.slice(0, 23)}…${known}` };
}

function checkAuthenticity(record: any, pubkeyB64: string | null): Check {
  // Python ile BİREBİR aynı arama sırası (verify.py check_authenticity): iki kaynak ×
  // iki ad. 2026-09-22: üretimdeki disclosure görünümü imzayı
  // `record_ref.signature_ed25519`'da taşıyor (platform attestation_views.py);
  // eski arama o alanı hiç görmüyordu → gerçek bir üretim kaydında Python PASS,
  // TS NOT MEASURED verdi. İki uygulamanın aynı kayıtta ayrışması KLM-5'in
  // önlemek için var olduğu arızadır; örnek kayıt bunu göstermiyordu çünkü
  // örnek, üretimin bu yolla verdiği şekilde değil.
  let sig: unknown = undefined;
  for (const src of [record.record_ref, record.meta]) {
    if (src && typeof src === "object") {
      sig = sig || src.record_signature || src.signature_ed25519;
    }
  }
  if (!sig || !String(sig).startsWith("ed25519:")) {
    return { status: UNMEASURED, tier: "unconditional",
             detail: "record carries no Ed25519 signature — an HMAC is not " +
                     "third-party verifiable (whoever can verify can also forge)" };
  }
  if (!pubkeyB64) {
    return { status: UNMEASURED, tier: "unconditional", detail: "--pubkey not supplied" };
  }
  try {
    // Ham 32 baytlık Ed25519 açık anahtarını SPKI'ya sararak node:crypto'ya veriyoruz.
    const raw = Buffer.from(pubkeyB64, "base64");
    const spki = Buffer.concat([
      Buffer.from("302a300506032b6570032100", "hex"), raw,
    ]);
    const key = createPublicKey({ key: spki, format: "der", type: "spki" });
    const ok = edVerify(null, Buffer.from(claimedSignature(record) ?? "", "utf8"),
                        key, Buffer.from(String(sig).slice("ed25519:".length), "base64"));
    return { status: ok ? OK : FAIL, tier: "unconditional",
             detail: ok ? "signature verified against the published public key"
                        : "signature did not verify" };
  } catch (e) {
    return { status: FAIL, tier: "unconditional",
             detail: `signature did not verify: ${(e as Error).name}` };
  }
}

function checkGammaInvariant(record: any): Check {
  const found: Array<[string, number, number]> = [];
  for (const [path, val] of walk(record)) {
    if (path.endsWith("declared_confidence") && typeof val === "number") {
      const base = path.slice(0, path.lastIndexOf("."));
      const node = at(record, base) ?? {};
      if (typeof node.grounded_confidence === "number" && typeof node.gap === "number") {
        found.push([base, +(val - node.grounded_confidence).toFixed(6), +node.gap.toFixed(6)]);
      }
    }
  }
  if (!found.length) {
    return { status: UNMEASURED, tier: "unconditional",
             detail: "no declared/grounded/gap triple found in record" };
  }
  const bad = found.filter(([, d, g]) => Math.abs(d - g) > 1e-6);
  return { status: bad.length ? FAIL : OK, tier: "unconditional",
           detail: bad.length ? `${bad.length}/${found.length} triples do not hold`
                              : plural(found.length, "triple") };
}

/** Manifest null'ları AYRI sözleşmeye tabi — γ vektörünün kuralıyla denetlenmez. */
const BARE_NULL_OK = ["composition."];

function checkHonestNulls(record: any): Check {
  const paths = [...walk(record)].map(([p]) => p);
  const naked: string[] = [];
  for (const [path, val] of walk(record)) {
    if (val !== null) continue;
    if (/_(reason|status|basis)$/.test(path)) continue;
    if (BARE_NULL_OK.some((seg) => path.includes(seg))) continue;
    const parent = path.slice(0, path.lastIndexOf("."));
    const leaf = path.slice(path.lastIndexOf(".") + 1);
    const siblings = paths.filter((p) => p.startsWith(parent + ".") && p !== path);
    const hasReason = siblings.some((s) =>
      /_(reason|status|basis)$/.test(s) || s.includes("epistemic_status") || s.includes(leaf));
    if (!hasReason) naked.push(path);
  }
  return { status: naked.length ? FAIL : OK, tier: "unconditional",
           detail: naked.length ? `${naked.length} nulls without a reason: ${naked.slice(0, 3)}`
             : "every null in the γ vector carries a reason " +
               "(manifest nulls fall under a separate contract, out of scope)" };
}

function checkComposition(record: any): Check {
  let comp: any = null;
  for (const [path] of walk(record)) {
    if (path.endsWith("composition.schema")) {
      comp = at(record, path.slice(0, path.lastIndexOf(".")));
      break;
    }
  }
  if (!comp) {
    return { status: FAIL, tier: "unconditional",
             detail: "no composition manifest — scores cannot be reproduced" };
  }
  const missing = ["formulas", "calibration", "worker"].filter((k) => !(k in comp));
  return { status: missing.length ? FAIL : OK, tier: "unconditional",
           detail: missing.length ? `manifest missing fields: ${missing}`
             : `${comp.schema} · formulas+calibration+worker present` };
}

function checkClaimSupport(record: any): Check {
  const pairs: Array<[string, string, number]> = [];
  for (const [path, val] of walk(record)) {
    if (path.endsWith(".claim") && typeof val === "string") {
      const node = at(record, path.slice(0, path.lastIndexOf("."))) ?? {};
      const ev = node.evidence_text ?? node.evidence_sentence;
      if (typeof ev === "string" && typeof node.claim_support === "number") {
        pairs.push([val, ev, node.claim_support]);
      }
    }
  }
  if (!pairs.length) {
    return { status: UNMEASURED, tier: "conditional",
             detail: "record carries no claim+evidence text — this tier is " +
                     "verifiable only in the full-disclosure view" };
  }
  const toks = (t: string) =>
    new Set((t.match(/[^\W\d_]{3,}/gu) ?? []).map((w) => w.toLowerCase()));
  const bad = pairs.filter(([claim, ev, sc]) => {
    const ct = toks(claim);
    if (!ct.size) return sc !== 0;
    let hit = 0;
    for (const w of ct) if (toks(ev).has(w)) hit++;
    return Math.abs(+(hit / ct.size).toFixed(4) - sc) > 0.01;
  });
  return { status: bad.length ? FAIL : OK, tier: "conditional",
           detail: bad.length ? `${bad.length}/${pairs.length} recomputations disagree`
                              : plural(pairs.length, "claim", ["reproduced", "reproduced"]) };
}

const NOT_VERIFIABLE: Array<[string, string]> = [
  ["coherence", "requires the embedding model + calibration artefacts"],
  ["attention attribution", "requires the worker's internal state"],
  ["whether the answer is CORRECT", "this is a provenance system, not a truth oracle"],
];

/** `1 triple holds` / `3 triples hold` — subject and verb agree.
 *  Mirrors `_plural` in verify.py so the two implementations render
 *  identical prose, not merely identical verdicts. */
function plural(n: number, singular: string,
                verb: [string, string] = ["holds", "hold"]): string {
  return `${n} ${singular}${n === 1 ? "" : "s"} ${n === 1 ? verb[0] : verb[1]}`;
}

export function run(record: any, pubkey: string | null) {
  // [stable_id, display name, result]. The ID is the machine contract;
  // the display name is prose. Must stay in lockstep with CHECKS in
  // verify.py — the two implementations are only a real cross-check if a
  // consumer can line their outputs up field by field.
  const rows: Array<[string, string, Check]> = [
    ["content_integrity",       "content integrity",           checkIntegrity(record)],
    ["authenticity_ed25519",    "authenticity (Ed25519)",      checkAuthenticity(record, pubkey)],
    ["gamma_invariant",         "γ invariant",                 checkGammaInvariant(record)],
    ["honest_nulls",            "honest-null discipline",      checkHonestNulls(record)],
    ["composition_manifest",    "composition manifest",        checkComposition(record)],
    ["claim_support_recompute", "claim_support recomputation", checkClaimSupport(record)],
  ];
  const { accepted } = decide(rows, true);
  return { rows, ok: accepted };
}

// ── Acceptance profile ──────────────────────────────────────────────────
//
// Mirrors verify.py's ACCEPTANCE_PROFILE / REQUIRED_CHECKS exactly. A
// delivery gate MUST NOT read a bare `ok` computed as "did anything
// explicitly fail?": `NOT MEASURED` is not `FAIL`, but it is not `PASS`
// either, and counting it as one violates the project's first principle
// (CLAUDE.md §3.1, not-known ≠ zero).
//
// content_integrity and authenticity_ed25519 are BOTH required and neither
// implies the other: the signature covers the DECLARED hash, so editing the
// body is caught only by integrity, and stripping the signature is caught
// only by authenticity.
export const ACCEPTANCE_PROFILE = "nage-acceptance/1";
export const REQUIRED_CHECKS = [
  "content_integrity",
  "authenticity_ed25519",
  "gamma_invariant",
  "honest_nulls",
  "composition_manifest",
] as const;

// 0 accepted · 2 rejected with a real FAIL · 3 rejected only as unmeasured.
// NOT MEASURED is not the same diagnosis as FAIL — but it is not PASS either.
export function exitCode(rows: Array<[string, string, Check]>, strict = true): number {
  const { accepted } = decide(rows, strict);
  if (accepted) return 0;
  return rows.some(([, , r]) => r.status === FAIL) ? 2 : 3;
}

export function decide(rows: Array<[string, string, Check]>, strict = true):
    { accepted: boolean; reasons: string[] } {
  const byId = new Map(rows.map(([cid, , r]) => [cid, r]));
  if (!strict) {
    const failed = rows
      .filter(([, , r]) => r.status === FAIL && r.tier === "unconditional")
      .map(([cid]) => `${cid}: FAIL`);
    return { accepted: failed.length === 0, reasons: failed };
  }
  const reasons: string[] = [];
  for (const cid of REQUIRED_CHECKS) {
    const r = byId.get(cid);
    if (!r) reasons.push(`${cid}: check absent from this verifier build`);
    else if (r.status !== OK) reasons.push(`${cid}: ${r.status} (required to be ${OK})`);
  }
  for (const [cid, , r] of rows) {
    if (r.status === FAIL && !(REQUIRED_CHECKS as readonly string[]).includes(cid)) {
      reasons.push(`${cid}: FAIL`);
    }
  }
  return { accepted: reasons.length === 0, reasons };
}

function render(rows: Array<[string, string, Check]>, ok: boolean, strict = true) {
  const w = Math.max(...rows.map(([, n]) => n.length));
  console.log();
  for (const [, name, r] of rows) {
    const mark = r.status === OK ? "✓" : r.status === FAIL ? "✗" : "·";
    const tier = r.tier === "unconditional" ? "unconditional" : "conditional";
    console.log(`  ${mark} ${name.padEnd(w)}  ${r.status.padEnd(13)} [${tier}]`);
    console.log(`    ${" ".repeat(w)}  ${r.detail}`);
  }
  console.log("\n  NOT VERIFIABLE FROM THIS RECORD (stated deliberately):");
  for (const [what, why] of NOT_VERIFIABLE) console.log(`    · ${what} — ${why}`);
  const { reasons } = decide(rows, strict);
  if (strict) {
    console.log(`\n  ACCEPTANCE PROFILE: ${ACCEPTANCE_PROFILE}`);
    console.log(`    required to PASS: ${REQUIRED_CHECKS.join(", ")}`);
    if (ok) {
      console.log("\n  RESULT: ACCEPTED — every required check PASSED\n");
    } else {
      console.log("\n  RESULT: NOT ACCEPTED");
      for (const why of reasons) console.log(`    · ${why}`);
      console.log("    NOT MEASURED is not FAIL — but it is not PASS either.\n");
    }
  } else {
    console.log("\n  MODE: diagnostic (NOT an acceptance gate)");
    console.log(`  RESULT: ${ok ? "no unconditional tier failed"
                                : "AN UNCONDITIONAL TIER FAILED"}`);
    console.log("    an unmeasured required check does NOT reject in this mode.\n");
  }
}

function selfTest(record: any, pubkey: string | null): number {
  console.log("\n── SELF-TEST: the record is deliberately corrupted ──");
  if (!run(record, pubkey).ok) {
    console.log("  the intact record already fails; the self-test is meaningless");
    return 1;
  }
  const mutations: Array<[string, (r: any) => boolean]> = [
    ["perturb a score", (r) => {
      for (const [path, val] of walk(r)) {
        if (typeof val === "number" && val > 0 && val < 1) {
          const parts = path.split(".");
          let node = r;
          for (const p of parts.slice(0, -1)) node = node[p];
          node[parts[parts.length - 1]] = Math.min(0.999, val + 0.137);
          return true;
        }
      }
      return false;
    }],
    ["break the signature", (r) => {
      const v = r.meta?.verification ?? r.verification;
      if (v?.signature) { v.signature = v.signature.slice(0, -4) + "0000"; return true; }
      return false;
    }],
    ["break the γ invariant via gap", (r) => {
      for (const [path, val] of walk(r)) {
        if (path.endsWith("gap") && typeof val === "number") {
          const parts = path.split(".");
          let node = r;
          for (const p of parts.slice(0, -1)) node = node[p];
          node[parts[parts.length - 1]] = val + 0.25;
          return true;
        }
      }
      return false;
    }],
    // The blind spot that hid the fail-open: every mutation above CORRUPTS a
    // field, so authenticity returned FAIL and the aggregate turned red.
    // Removing the field returns NOT MEASURED, which the old rule counted as
    // "nothing failed". Strip it, and the gate must still reject.
    ["remove the signature entirely", (r) => {
      let hit = false;
      for (const key of ["record_ref", "meta"]) {
        const src = r[key];
        if (src && typeof src === "object") {
          for (const f of ["record_signature", "signature_ed25519"]) {
            if (src[f] !== undefined) { delete src[f]; hit = true; }
          }
        }
      }
      const v = r.meta?.verification ?? r.verification;
      if (v?.signature !== undefined) { delete v.signature; hit = true; }
      return hit;
    }],
  ];
  const survived: string[] = [];
  for (const [label, mut] of mutations) {
    const m = JSON.parse(JSON.stringify(record));
    if (!mut(m)) { console.log(`  · ${label.padEnd(34)} not applicable (target field absent)`); continue; }
    const { ok } = run(m, pubkey);
    console.log(`  · ${label.padEnd(34)} ${ok ? "✗ STILL PASSES" : "✓ turned red"}`);
    if (ok) survived.push(label);
  }

  // Tanınmayan algoritma beyanında kırmızıya dönmek YETMEZ (verify.py
  // self_test ile birebir): koruma yokken bu dosya "sha256-canonical/9"u
  // eski yedekle hash'leyip PASS, verify.py FAIL veriyordu. İstenen teşhis:
  // ÖLÇÜLMEDİ + `unsupported_algorithm`. Boş dize ayrı satır: beyan VARLIKLA
  // belirlenir; doğruluk sınamasına dönülürse "" iki dilde de eski yola düşer.
  const misdiagnosed: string[] = [];
  const declarations: Array<[string, string]> = [
    ["declare an unknown algorithm", "sha256-canonical/9"],
    ["declare an empty algorithm", ""],
  ];
  for (const [label, value] of declarations) {
    const m = JSON.parse(JSON.stringify(record));
    if (!mutateAlgorithm(m, value)) {
      console.log(`  · ${label.padEnd(34)} not applicable (target field absent)`);
      continue;
    }
    const ci = run(m, pubkey).rows.find(([cid]) => cid === "content_integrity")![2];
    const right = ci.status === UNMEASURED && ci.detail.startsWith("unsupported_algorithm");
    console.log(`  · ${label.padEnd(34)} ${right ? "✓ NOT MEASURED, not FAIL" : "✗ " + ci.status}`);
    if (!right) misdiagnosed.push(label);
  }

  if (survived.length) {
    console.log("\n  THE VERIFIER IS NOT MEASURING: a corrupted record still passed →", survived);
  }
  if (misdiagnosed.length) {
    console.log("\n  WRONG DIAGNOSIS: an unknown algorithm must read NOT MEASURED " +
                "(unsupported_algorithm), not a verdict →", misdiagnosed);
  }
  if (survived.length || misdiagnosed.length) return 1;
  console.log("\n  the verifier catches corruption ✓\n");
  return 0;
}

/** Algoritma beyanını değiştirir — `algorithmOf` ile aynı sırada (önce meta). */
function mutateAlgorithm(r: any, value: unknown): boolean {
  for (const ver of [r.meta?.verification, r.verification]) {
    if (ver !== null && typeof ver === "object" && !Array.isArray(ver)) {
      ver.algorithm = value;
      return true;
    }
  }
  return false;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const args = process.argv.slice(2);
  const file = args.find((a) => !a.startsWith("--"));
  if (!file) {
    console.error("usage: verify.ts <receipt.json> [--pubkey <file>] " +
                  "[--self-test] [--json] [--diagnostic]");
    process.exit(64);
  }
  const pkIdx = args.indexOf("--pubkey");
  const pubkey = pkIdx >= 0 ? readFileSync(args[pkIdx + 1], "utf8").trim() : null;
  const record = JSON.parse(readFileSync(file, "utf8"));
  if (args.includes("--self-test")) process.exit(selfTest(record, pubkey));
  const strict = !args.includes("--diagnostic");
  const { rows } = run(record, pubkey);
  const { accepted, reasons } = decide(rows, strict);
  if (args.includes("--json")) {
    console.log(JSON.stringify({
      ok: accepted,
      accepted,
      mode: strict ? "acceptance" : "diagnostic",
      profile: strict ? ACCEPTANCE_PROFILE : null,
      required_checks: [...REQUIRED_CHECKS],
      rejection_reasons: reasons,
      exit_code: exitCode(rows, strict),
      checks: Object.fromEntries(rows.map(([cid, name, r]) => [cid, { ...r, name }])),
      not_verifiable: Object.fromEntries(NOT_VERIFIABLE),
    }, null, 2));
  } else {
    render(rows, accepted, strict);
  }
  process.exit(exitCode(rows, strict));
}
