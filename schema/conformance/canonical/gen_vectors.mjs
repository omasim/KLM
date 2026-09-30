// Generates vectors.json for klm-canonical/1 from the Node reference
// (jcs_reference.mjs). Expected outputs and hashes are COMPUTED here by the
// JavaScript engine — never typed by hand. Inputs are JSON texts that parse to
// the same value in JavaScript (JSON.parse) and Python (json.loads).
//
//   node gen_vectors.mjs            # rewrites vectors.json next to this file
import { createHash } from "node:crypto";
import { writeFileSync } from "node:fs";
import { canonicalize } from "./jcs_reference.mjs";

const J = (v) => JSON.stringify(v); // helper: build an input text from a JS literal

// RFC 8785 Appendix B: IEEE-754 bit patterns. Only the bit patterns are written
// here; the input text is the exact 17-significant-digit form of that double
// (toExponential(16)) and the expected output is whatever the engine prints.
const appendixB = [
  "0000000000000000", "8000000000000000", "0000000000000001", "8000000000000001",
  "7fefffffffffffff", "ffefffffffffffff", "4340000000000000", "c340000000000000",
  "4430000000000000", "44b52d02c7e14af5", "44b52d02c7e14af6", "44b52d02c7e14af7",
  "444b1ae4d6e2ef4e", "444b1ae4d6e2ef4f", "444b1ae4d6e2ef50", "3eb0c6f7a0b5ed8c",
  "3eb0c6f7a0b5ed8d", "41b3de4355555553", "41b3de4355555554", "41b3de4355555555",
  "41b3de4355555556", "41b3de4355555557", "becbf647612f3696", "43143ff3c1cb0959",
];
const fromBits = (hex) => {
  const dv = new DataView(new ArrayBuffer(8));
  dv.setBigUint64(0, BigInt("0x" + hex));
  return dv.getFloat64(0);
};
const bitsText = (x) => (Object.is(x, -0) ? "-0.0" : x.toExponential(16)); // float text in Python too

const cases = [
  // ── E1: integral floats (the defect) ──
  ["integral-float-one", "1.0 — Python legacy writes 1.0, JCS writes 1", "1.0"],
  ["integral-float-zero", "0.0 — Python legacy writes 0.0, JCS writes 0", "0.0"],
  ["negative-zero", "-0 serialises as 0", "-0.0"],
  ["e1-record", "the E1 shape: a score of exactly 1.0 / 0.0 inside a record",
    '{"label":"STABLE","claim_support":1.0,"coherence":0.0,"gap":-0.0,"grounded":0.75}'],
  // ── exponent boundaries (ES Number::toString) ──
  ["exp-1e21", "first power of ten written with an exponent", "1e21"],
  ["plain-1e20", "last power of ten written in full", "1e20"],
  ["exp-1e-7", "first small power written with an exponent", "1e-7"],
  ["exp-1.5e-7", "multi-digit mantissa below 1e-6", "1.5e-7"],
  ["plain-1e-6", "last small power written in full", "0.000001"],
  ["plain-big-integral", "integral double below 1e21, input as a float text", "123456789012345680000.0"],
  ["sum-0.1-0.2", "0.1+0.2 — shortest round-trip keeps all 17 digits", "0.30000000000000004"],
  ["overlong-input", "over-precise input collapses to shortest round-trip", "0.1000000000000000055511151231257827"],
  ["min-subnormal", "smallest positive double", "5e-324"],
  ["max-double", "largest finite double", "1.7976931348623157e308"],
  ["rfc-1e30", "RFC 8785 §3.2.2.3 example", "1E30"],
  ["rfc-4.50", "RFC 8785 §3.2.2.3 example (trailing zero dropped)", "4.50"],
  ["rfc-2e-3", "RFC 8785 §3.2.2.3 example", "2e-3"],
  ["rfc-1e-27", "RFC 8785 §3.2.2.3 example", "0.000000000000000000000000001"],
  ["rfc-333333333.33333329", "RFC 8785 §3.2.2.3 example", "333333333.33333329"],
  ["int-42", "integer", "42"],
  ["int-max-safe", "Number.MAX_SAFE_INTEGER", "9007199254740991"],
  ["int-min-safe", "-Number.MAX_SAFE_INTEGER", "-9007199254740991"],
  ["int-negative-zero", "integer -0", "-0"],
  // ── strings ──
  ["string-control-escapes", "U+0000..U+001F: short escapes for \\b\\t\\n\\f\\r, \\u00xx (lowercase) otherwise",
    J(Array.from({ length: 32 }, (_, i) => String.fromCharCode(i)).join(""))],
  ["string-quote-backslash-slash", "\" and \\ escaped; / NOT escaped (input uses \\/)", '"q\\"b\\\\s\\/"'],
  ["string-del-and-line-separators", "U+007F, U+2028, U+2029 emitted verbatim", '"\\u007f\\u2028\\u2029"'],
  ["string-non-ascii", "non-ASCII emitted as raw UTF-8, astral included", '"çığ€\\ud83d\\ude00"'],
  ["rfc-string", "RFC 8785 §3.2.2.2 string example", '"\\u20ac$\\u000F\\u000aA\'\\u0042\\u0022\\u005c\\\\\\"\\/"'],
  // ── key ordering ──
  ["keys-rfc-sort", "RFC 8785 §3.2.3 sorting example (UTF-16 code units)",
    '{"\\u20ac":"Euro Sign","\\r":"Carriage Return","\\ufb33":"Hebrew Letter Dalet With Dagesh","1":"One","\\ud83d\\ude00":"Emoji: Grinning Face","\\u0080":"Control","\\u00f6":"Latin Small Letter O With Diaeresis"}'],
  ["keys-astral-before-high-bmp", "U+1F600 (D83D DE00) sorts BEFORE U+FB33 in UTF-16; code-point order says the opposite",
    '{"\\ufb33":"bmp","\\ud83d\\ude00":"astral"}'],
  ["keys-prefix-and-case", "prefix sorts first; uppercase before lowercase", '{"ab":1,"a":2,"B":3,"b":4,"":5}'],
  // ── structure ──
  ["nested", "nested arrays/objects, array order preserved, keys sorted at every depth",
    '{"z":[1,[2.0,{"b":null,"a":true}],{}],"a":{"c":[],"b":false}}'],
  ["whitespace-dropped", "insignificant whitespace in input disappears", '{ "b" : [ 1 , 2 ] ,\n "a" : { } }'],
  ["literal-true", "top-level true", "true"],
  ["literal-false", "top-level false", "false"],
  ["literal-null", "top-level null", "null"],
  ["empty-object", "{}", "{}"],
  ["empty-array", "[]", "[]"],
  ["empty-string", '""', '""'],
  ["rfc-composite", "RFC 8785 §3.2.2 composite example",
    '{"numbers":[333333333.33333329,1E30,4.50,2e-3,0.000000000000000000000000001],"string":"\\u20ac$\\u000F\\u000aA\'\\u0042\\u0022\\u005c\\\\\\"\\/","literals":[null,true,false]}'],
  ...appendixB.map((hex) => [`rfc-appendix-b-${hex}`, `RFC 8785 Appendix B, IEEE-754 bits ${hex}`, bitsText(fromBits(hex))]),
];

// Inputs a conforming canonicalizer MUST refuse (no canonical form exists).
const reject = [
  ["nan", "NaN (Python json.loads accepts it; JSON does not)", "NaN", true],
  ["infinity", "Infinity", "Infinity", true],
  ["negative-infinity", "-Infinity", "-Infinity", true],
  ["overflow-to-infinity", "1e400 parses to Infinity in both languages", "1e400", true],
  ["lone-high-surrogate", "lone surrogate in a string (not I-JSON)", '"\\ud800"', true],
  ["lone-low-surrogate-key", "lone surrogate in an object key", '{"\\udc00":1}', true],
  ["int-above-max-safe", "2^53 as an integer literal is outside ±(2^53-1). An implementation that parses exact integers MUST refuse it; a JavaScript parser already holds a double and cannot tell (2^53+1 would silently become 2^53), so only the exact-integer side is checked", "9007199254740992", false],
  ["int-below-min-safe", "-(2^53+1) as an integer literal", "-9007199254740993", false],
];

const out = {
  canonicalization: "klm-canonical/1",
  description: "Golden vectors for klm-canonical/1 (RFC 8785 JCS). `input` is a JSON text; `expected` is the canonical form as a string (hash its UTF-8 bytes); `sha256` is hex over those bytes. Generated by gen_vectors.mjs with the Node reference jcs_reference.mjs — do not edit by hand.",
  generated_with: `node ${process.version}`,
  cases: cases.map(([id, note, input]) => {
    const expected = canonicalize(JSON.parse(input));
    return { id, note, input, expected, sha256: createHash("sha256").update(expected, "utf8").digest("hex") };
  }),
  reject: reject.map(([id, note, input, jsRejects]) => {
    let js;
    try { canonicalize(JSON.parse(input)); js = false; } catch { js = true; }
    if (js !== jsRejects) throw new Error(`reject vector ${id}: JS reference rejects=${js}, declared ${jsRejects}`);
    return { id, note, input, js_reference_rejects: jsRejects };
  }),
};
const ids = new Set([...out.cases, ...out.reject].map((c) => c.id));
if (ids.size !== out.cases.length + out.reject.length) throw new Error("duplicate vector id");
writeFileSync(new URL("./vectors.json", import.meta.url), JSON.stringify(out, null, 1) + "\n");
console.log(`wrote vectors.json: ${out.cases.length} accept cases, ${out.reject.length} reject cases (${out.generated_with})`);
