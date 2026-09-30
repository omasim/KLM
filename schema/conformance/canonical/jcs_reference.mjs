// klm-canonical/1 reference (RFC 8785 JCS) — deliberately tiny, built only on
// ECMAScript primitives: JSON.stringify serialises numbers (Number::toString)
// and strings (minimal escapes) exactly as JCS requires; Array.prototype.sort
// with no comparator orders keys by UTF-16 code units. Everything else is
// refusal of inputs JCS has no canonical form for.
//
//   node jcs_reference.mjs < inputs.json   # stdin: JSON array of JSON *texts*
//                                          # stdout: JSON array of canonical strings
//                                          #         (or {"error": "..."} per item)
import { pathToFileURL } from "node:url";

const LONE = /[\ud800-\udbff](?![\udc00-\udfff])|(?<![\ud800-\udbff])[\udc00-\udfff]/;

export function canonicalize(v) {
  if (v === null || typeof v === "boolean") return JSON.stringify(v);
  if (typeof v === "number") {
    if (!Number.isFinite(v)) throw new Error(`non-finite number ${v}`);
    return JSON.stringify(v);                       // -0 -> "0", 1.0 -> "1", 1e21 -> "1e+21"
  }
  if (typeof v === "string") {
    if (LONE.test(v)) throw new Error("lone surrogate");
    return JSON.stringify(v);
  }
  if (Array.isArray(v)) return "[" + v.map(canonicalize).join(",") + "]";
  const keys = Object.keys(v).sort();               // UTF-16 code-unit order
  return "{" + keys.map((k) => canonicalize(k) + ":" + canonicalize(v[k])).join(",") + "}";
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  let buf = "";
  process.stdin.setEncoding("utf8");
  process.stdin.on("data", (c) => (buf += c));
  process.stdin.on("end", () => {
    const out = JSON.parse(buf).map((text) => {
      try { return canonicalize(JSON.parse(text)); } catch (e) { return { error: String(e.message) }; }
    });
    process.stdout.write(JSON.stringify(out));
  });
}
