#!/usr/bin/env python3
"""KLM attestation-record validator — reference implementation, klm-attestation/0.1.

Stdlib-only. Enforces the structural contract of klm-attestation.schema.json
plus the semantic rules JSON Schema cannot express, and renders a KLM-0
"Declared" verdict per KLM Spec §8.3:

  KLM-0 = emits a record with the §6 structure; supports the
  epistemic-status vocabulary; returns explicit nulls; fabricates no signal.

It also renders the KLM-1 "Traceable" verdict (§8.3): generative inputs and
key events replayably recorded — model version + configuration, retrieval
trace (source refs, timestamps, content hashes), knowledge-unit ids, loaded
procedures, output spans.

Usage:
    python3 validate_attestation.py [--level 0|1] record.json [record2.json ...]
Default --level 1: reports the highest level each record reaches; exit 0 when
every record reaches the requested level.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from validate_gamma import validate as validate_gamma_record  # noqa: E402

SCHEMA_ID = "klm-attestation/0.1"
STATUSES = {"measured", "heuristic", "synthesized", "unavailable"}
SOURCE_CLASSES = {
    "authoritative_record", "external_volatile", "user_assertion",
    "tool_result", "prior_summary", "model_generated",
}
SUPPORT_STATUSES = {"supported", "contradicted", "unsupported", "unknown"}
ACTIVATION_STATUSES = {"loaded", "triggered", "activated", "not_activated"}
GOV_NAMESPACES = {"safety", "privacy", "regulatory", "authorization", "audience", "scope"}
GOV_STATUSES = {"pass", "fail", "unknown", "not_applicable"}
LIFECYCLES = {"draft", "active", "disputed", "superseded", "expired",
              "revoked", "deleted", "legally_retained"}
EDGE_TYPES = {"supports", "expressed_as", "activated", "assessed_by",
              "derived_from", "supersedes"}
ATTRIBUTION_LEVELS = {"behavioral_association", "execution_attribution", "causal_contribution"}
EPS = 1e-6


def _is_unit(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and 0.0 <= v <= 1.0


def _req_str(obj: dict, key: str, where: str, errs: list[str]) -> str | None:
    v = obj.get(key)
    if not isinstance(v, str) or not v:
        errs.append(f"{where}.{key} must be a non-empty string")
        return None
    return v


def validate(record: dict) -> list[str]:
    errs: list[str] = []
    e = errs.append
    if not isinstance(record, dict):
        return ["record is not a JSON object"]
    if record.get("schema") != SCHEMA_ID:
        e(f"schema must be '{SCHEMA_ID}' (got {record.get('schema')!r})")

    # ── §6.1 inference block ──
    inf = record.get("inference")
    if not isinstance(inf, dict):
        e("inference block is required")
    else:
        _req_str(inf, "id", "inference", errs)
        _req_str(inf, "timestamp", "inference", errs)
        model = inf.get("model")
        if not isinstance(model, dict):
            e("inference.model is required")
        else:
            _req_str(model, "identifier", "inference.model", errs)
            _req_str(model, "version", "inference.model", errs)

    # ── collections + id uniqueness ──
    ids: dict[str, str] = {}  # id → collection

    def collect(kind: str, items) -> list[dict]:
        if items is None:
            e(f"{kind} array is required (may be empty)")
            return []
        if not isinstance(items, list):
            e(f"{kind} must be an array")
            return []
        out = []
        for i, obj in enumerate(items):
            if not isinstance(obj, dict):
                e(f"{kind}[{i}] must be an object")
                continue
            oid = obj.get("id")
            if not isinstance(oid, str) or not oid:
                e(f"{kind}[{i}].id must be a non-empty string")
                continue
            if oid in ids:
                e(f"duplicate object id '{oid}' ({ids[oid]} vs {kind})")
            ids[oid] = kind
            out.append(obj)
        return out

    kus = collect("knowledge_contributions", record.get("knowledge_contributions"))
    evs = collect("evidence", record.get("evidence"))
    cls = collect("claims", record.get("claims"))
    prs = collect("procedures", record.get("procedures"))
    sps = collect("spans", record.get("spans", []))
    gov = record.get("governance") or {}
    gas = collect("governance.assessments", gov.get("assessments", [])) if isinstance(gov, dict) else []

    # ── knowledge units (§2.1) ──
    for ku in kus:
        w = f"knowledge_unit[{ku['id']}]"
        if "content" not in ku:
            e(f"{w}.content is required (value or reference)")
        origin = ku.get("origin")
        if origin not in ("parametric", "injected"):
            e(f"{w}.origin must be parametric|injected")
        if ku.get("function") not in ("declarative", "procedural"):
            e(f"{w}.function must be declarative|procedural")
        if ku.get("epistemic_status") not in STATUSES:
            e(f"{w}.epistemic_status must be one of {sorted(STATUSES)}")
        sc = ku.get("source_class", "MISSING")
        sr = ku.get("source_reference", "MISSING")
        if origin == "parametric":
            # §2.1: null if parametric — a parametric unit claiming a bare
            # source is fabrication. This stays enforced (a monolithic
            # emitter still cannot fake provenance here).
            if sr is not None:
                e(f"{w}.source_reference must be null for parametric origin")
            if sc is not None:
                e(f"{w}.source_class must be null for parametric origin")
            # Amendment "Attested Parametric Sources" (spec v0.2): a unit
            # with MECHANICAL parametric attribution MAY carry a separate
            # parametric_attribution block. Optional; when present, all
            # four fields + status discipline MUST hold. The plain
            # source_reference above still stays null — the block is
            # deliberately separate so legacy fabrication stays rejected.
            pa = ku.get("parametric_attribution")
            if pa is not None:
                if not isinstance(pa, dict):
                    e(f"{w}.parametric_attribution must be an object")
                else:
                    mech = pa.get("mechanism")
                    if not isinstance(mech, str) or not mech:
                        e(f"{w}.parametric_attribution.mechanism must be a versioned id "
                          f"(deterministic, counterfactually-checkable — not model self-report)")
                    contrib = pa.get("contribution")
                    if not isinstance(contrib, (int, float)) or not (0.0 <= float(contrib) <= 1.0):
                        e(f"{w}.parametric_attribution.contribution must be a unit float [0,1]")
                    # Condition 2: contribution is a MEASURED quantity — the
                    # unit's epistemic_status carries it; enforce measured.
                    if ku.get("epistemic_status") != "measured":
                        e(f"{w}.parametric_attribution present ⇒ epistemic_status must be 'measured' "
                          f"(contribution is a measured share, §Amendment cond.2)")
                    tsr = pa.get("training_source_reference")
                    if not isinstance(tsr, str) or not tsr:
                        e(f"{w}.parametric_attribution.training_source_reference must be an "
                          f"addressable artifact id (hash/version — not a prose description)")
                    tsc = pa.get("training_source_class")
                    if tsc not in SOURCE_CLASSES:
                        e(f"{w}.parametric_attribution.training_source_class must be a §2.5 class")
        elif origin == "injected":
            if sc not in SOURCE_CLASSES:
                e(f"{w}.source_class must be a §2.5 class for injected origin")
        lc = ku.get("lifecycle")
        if lc is not None and lc not in LIFECYCLES:
            e(f"{w}.lifecycle '{lc}' not a §10.1 state")

    # ── evidence (§2.3) ──
    for ev in evs:
        if ev.get("source_class") not in SOURCE_CLASSES:
            e(f"evidence[{ev['id']}].source_class must be one of {sorted(SOURCE_CLASSES)}")
        rs = ev.get("retrieval_score")
        if rs is not None and not _is_unit(rs):
            e(f"evidence[{ev['id']}].retrieval_score must be in [0,1] or null")

    # ── claims (§2.2) ──
    for cl in cls:
        w = f"claim[{cl['id']}]"
        span = cl.get("text_span")
        if not (isinstance(span, dict)
                and isinstance(span.get("start"), int) and isinstance(span.get("end"), int)
                and 0 <= span["start"] <= span["end"]):
            e(f"{w}.text_span must be integers 0 <= start <= end")
        if cl.get("support_status") not in SUPPORT_STATUSES:
            e(f"{w}.support_status must be one of {sorted(SUPPORT_STATUSES)}")

    # ── procedures (§2.4) ──
    for pr in prs:
        w = f"procedure[{pr['id']}]"
        if not isinstance(pr.get("trigger"), str) or not pr.get("trigger"):
            e(f"{w}.trigger is required")
        if not isinstance(pr.get("trigger_result"), bool):
            e(f"{w}.trigger_result must be a boolean")
        status = pr.get("activation_status")
        if status not in ACTIVATION_STATUSES:
            e(f"{w}.activation_status must be one of {sorted(ACTIVATION_STATUSES)}")
        if status == "activated" and pr.get("trigger_result") is False:
            e(f"{w}: activated procedure with trigger_result=false is incoherent")
        spans = pr.get("affected_spans")
        if not isinstance(spans, list):
            e(f"{w}.affected_spans must be an array of span ids")
        else:
            for sid in spans:
                if sid not in ids or ids[sid] != "spans":
                    e(f"{w}.affected_spans references unknown span '{sid}'")

    # ── spans (§2.6) ──
    for sp in sps:
        if not (isinstance(sp.get("start"), int) and isinstance(sp.get("end"), int)
                and 0 <= sp["start"] <= sp["end"]):
            e(f"span[{sp['id']}] must have integers 0 <= start <= end")

    # ── governance (§5 L5 + §9) ──
    policy_ids = set()
    pols = gov.get("policies", []) if isinstance(gov, dict) else []
    if isinstance(pols, list):
        for pol in pols:
            if isinstance(pol, dict) and isinstance(pol.get("id"), str):
                policy_ids.add(pol["id"])
                if not isinstance(pol.get("version"), str) or not pol.get("version"):
                    e(f"governance.policies[{pol['id']}].version is required (§5 L5 provenance)")
    for ga in gas:
        w = f"governance.assessment[{ga['id']}]"
        if ga.get("namespace") not in GOV_NAMESPACES:
            e(f"{w}.namespace must be one of {sorted(GOV_NAMESPACES)}")
        if ga.get("status") not in GOV_STATUSES:
            e(f"{w}.status must be one of {sorted(GOV_STATUSES)}")
        for k in ("policy_id", "policy_version"):
            if not isinstance(ga.get(k), str) or not ga.get(k):
                e(f"{w}.{k} is required")
        pid = ga.get("policy_id")
        if policy_ids and isinstance(pid, str) and pid not in policy_ids:
            e(f"{w}.policy_id '{pid}' has no matching governance.policies entry")
        ro = ga.get("responsible_object")
        if not isinstance(ro, str) or ro not in ids or ids[ro] == "governance.assessments":
            e(f"{w}.responsible_object must reference a generative object id")
        st = ga.get("epistemic_status")
        if st is not None and st not in STATUSES:
            e(f"{w}.epistemic_status must be one of {sorted(STATUSES)}")

    # ── metacognition (§5 L4) + honest null / no fabrication ──
    nulls = record.get("nulls", {})
    if not isinstance(nulls, dict):
        e("nulls must be an object")
        nulls = {}
    for sig, entry in nulls.items():
        if not (isinstance(entry, dict) and isinstance(entry.get("reason"), str) and entry["reason"]):
            e(f"nulls.{sig} must carry a non-empty reason")

    meta = record.get("metacognition")
    if isinstance(meta, dict):
        declared = meta.get("declared_confidence")
        if declared is None:
            if "declared_confidence" in meta and "metacognition.declared_confidence" not in nulls:
                e("metacognition.declared_confidence is null without a nulls entry")
        elif not _is_unit(declared):
            e("metacognition.declared_confidence must be in [0,1] or honest-null")
        grounded = meta.get("grounded_confidence")
        gval = None
        if isinstance(grounded, dict):
            if not isinstance(grounded.get("formula"), str) or not grounded.get("formula"):
                e("metacognition.grounded_confidence.formula is required (replayability)")
            if _is_unit(grounded.get("value")):
                gval = grounded["value"]
            else:
                e("metacognition.grounded_confidence.value must be in [0,1]")
            comps = grounded.get("components")
            if not (isinstance(comps, dict) and comps and all(_is_unit(v) for v in comps.values())):
                e("metacognition.grounded_confidence.components must be non-empty [0,1] map (no collapse)")
        gap = meta.get("gap")
        if _is_unit(declared) and gval is not None:
            if not isinstance(gap, (int, float)) or abs(gap - (declared - gval)) > EPS:
                e("metacognition.gap must equal declared - grounded.value")
        status_map = meta.get("signal_status", {})
        if isinstance(status_map, dict):
            for sig, st in status_map.items():
                if st not in STATUSES:
                    e(f"metacognition.signal_status.{sig} = {st!r} invalid")
                if st == "unavailable" and meta.get(sig) is not None and sig in meta:
                    e(f"metacognition.{sig} marked unavailable but carries a value — fabricated signal")

    # ── relations (§6.2) — typed edges + referential integrity ──
    rels = record.get("relations")
    if isinstance(rels, list):
        for i, edge in enumerate(rels):
            if not isinstance(edge, dict):
                e(f"relations[{i}] must be an object")
                continue
            etype = edge.get("type")
            if etype not in EDGE_TYPES and not (isinstance(etype, str) and ":" in etype):
                e(f"relations[{i}].type '{etype}' is neither a §6.2 type nor namespaced (vendor:type)")
            for endpoint in ("from", "to"):
                ref = edge.get(endpoint)
                if not isinstance(ref, str) or ref not in ids:
                    if not (endpoint == "to" and etype in ("derived_from", "supersedes")
                            and isinstance(ref, str) and ref):
                        e(f"relations[{i}].{endpoint} '{ref}' does not reference a known object id")
            lvl = edge.get("attribution_level")
            if lvl is not None and lvl not in ATTRIBUTION_LEVELS:
                e(f"relations[{i}].attribution_level '{lvl}' invalid")
            if etype == "supports" and isinstance(edge.get("from"), str) and isinstance(edge.get("to"), str):
                if ids.get(edge["from"]) not in ("evidence",) or ids.get(edge["to"]) != "claims":
                    e(f"relations[{i}]: supports must run evidence → claim")
            if etype == "expressed_as" and ids.get(edge.get("to", "")) != "spans":
                e(f"relations[{i}]: expressed_as must target a span id")

    # ── embedded gamma ──
    gamma = record.get("gamma")
    if isinstance(gamma, dict):
        for gerr in validate_gamma_record(gamma):
            e(f"gamma: {gerr}")

    return errs


def validate_level1(record: dict) -> list[str]:
    """KLM-1 'Traceable' checks — run only on a KLM-0-clean record.

    Replayability floor: an independent party re-running the pipeline can
    reproduce the same trace. Machine-checkable minimums per §8.3 + §5 L1.
    """
    errs: list[str] = []
    e = errs.append

    inf = record.get("inference", {})
    if inf.get("configuration") is None and "inference.configuration" not in record.get("nulls", {}):
        e("KLM-1: inference.configuration must be recorded (or an honest null with reason)")

    # Retrieval trace — every evidence object replayable.
    for ev in record.get("evidence", []):
        w = f"evidence[{ev.get('id')}]"
        for k in ("source_reference", "retrieved_at", "content_hash"):
            if not ev.get(k):
                e(f"KLM-1: {w}.{k} is required for a replayable retrieval trace")

    # Injected knowledge units must be resolvable.
    for ku in record.get("knowledge_contributions", []):
        if ku.get("origin") == "injected" and not ku.get("source_reference"):
            e(f"KLM-1: knowledge_unit[{ku.get('id')}] is injected but has no source_reference")

    # Output spans recorded whenever there is output structure to anchor.
    spans = record.get("spans", [])
    claims = record.get("claims", [])
    if claims and not spans:
        e("KLM-1: claims exist but no output spans are recorded")
    span_ids = {s.get("id") for s in spans if isinstance(s, dict)}
    expressed = {edge.get("from") for edge in record.get("relations", [])
                 if isinstance(edge, dict) and edge.get("type") == "expressed_as"
                 and edge.get("to") in span_ids}
    for cl in claims:
        if cl.get("id") not in expressed:
            e(f"KLM-1: claim[{cl.get('id')}] has no expressed_as edge to an output span")

    return errs


def validate_level2(record: dict) -> list[str]:
    """KLM-2 'Grounded' checks — claim↔evidence + procedure↔execution
    links with mechanical floors; L1 vector and L2 attribution present
    (Spec §8.3). Run only on a KLM-1-clean record."""
    errs: list[str] = []
    e = errs.append

    claims = record.get("claims", [])
    nulls = record.get("nulls", {})
    if not claims and "claims" not in nulls:
        e("KLM-2: no claim decomposition (empty claims without an honest-null reason)")

    # L1 vector — five fields, versioned claim_support formula, and the
    # relevance≠support distinction made explicit.
    l1 = (record.get("ext") or {}).get("klm_l1")
    if not isinstance(l1, dict):
        e("KLM-2: ext.klm_l1 (L1 vector) is required")
    else:
        l1_nulls = l1.get("nulls", {})
        for k in ("retrieval_relevance", "claim_support", "evidence_coverage",
                  "source_authority", "source_freshness"):
            if k not in l1:
                e(f"KLM-2: ext.klm_l1.{k} missing")
            elif l1[k] is None and k not in l1_nulls and k not in nulls:
                e(f"KLM-2: ext.klm_l1.{k} is null without a reason")
            elif l1[k] is not None and not _is_unit(l1[k]):
                e(f"KLM-2: ext.klm_l1.{k} must be in [0,1] or honest-null")
        formulas = l1.get("formulas")
        if not (isinstance(formulas, dict) and isinstance(formulas.get("claim_support"), str)):
            e("KLM-2: ext.klm_l1.formulas.claim_support (versioned mechanical floor) is required")

    # Claim-side link discipline: supported claims must carry a supports
    # edge; supports edges must land on supported/contradicted claims
    # (presence-of-source reported as support is the violation KLM exists
    # to catch).
    supports_to = {}
    for edge in record.get("relations", []):
        if isinstance(edge, dict) and edge.get("type") == "supports":
            supports_to.setdefault(edge.get("to"), []).append(edge.get("from"))
    claim_status = {c.get("id"): c.get("support_status") for c in claims}
    for cid, status in claim_status.items():
        if status == "supported" and cid not in supports_to:
            e(f"KLM-2: claim[{cid}] is 'supported' but has no supports edge")
    for cid in supports_to:
        if claim_status.get(cid) not in ("supported", "contradicted"):
            e(f"KLM-2: supports edge lands on claim[{cid}] whose status is "
              f"'{claim_status.get(cid)}' — presence is not support")

    # Procedure→execution links: an activated procedure must have an
    # activated edge (execution attribution floor).
    activated_from = {edge.get("from") for edge in record.get("relations", [])
                      if isinstance(edge, dict) and edge.get("type") == "activated"}
    for pr in record.get("procedures", []):
        if pr.get("activation_status") == "activated" and pr.get("id") not in activated_from:
            e(f"KLM-2: procedure[{pr.get('id')}] activated without an activated edge")

    return errs


def validate_level3(record: dict) -> list[str]:
    """KLM-3 'Reflective' checks — L4 split confidence + L5 deterministic
    governance with policy provenance, as independent traces (§8.1, §8.3).
    Run only on a KLM-2-clean record."""
    errs: list[str] = []
    e = errs.append
    nulls = record.get("nulls", {})

    # L4 — split confidence must be present (or an honest null explains why).
    meta = record.get("metacognition")
    if not isinstance(meta, dict):
        if "metacognition" not in nulls:
            e("KLM-3: metacognition block is required (declared/grounded/gap)")
    else:
        if meta.get("declared_confidence") is None and "metacognition.declared_confidence" not in nulls:
            e("KLM-3: metacognition.declared_confidence missing")
        grounded = meta.get("grounded_confidence")
        if not isinstance(grounded, dict):
            e("KLM-3: metacognition.grounded_confidence (with components) is required")
        if meta.get("gap") is None and meta.get("declared_confidence") is not None:
            e("KLM-3: metacognition.gap missing")

    # L5 — governance with reflective independence + policy provenance.
    gov = record.get("governance")
    if not isinstance(gov, dict):
        e("KLM-3: governance block is required")
        return errs
    engine = gov.get("engine")
    if not (isinstance(engine, dict) and engine.get("identifier") and engine.get("version")):
        e("KLM-3: governance.engine {identifier, version} is required (§8.1 independence)")
    else:
        model_id = (record.get("inference", {}).get("model") or {}).get("identifier")
        if engine.get("identifier") == model_id:
            e("KLM-3: governance.engine equals inference.model — the judge "
              "must not be the author (self-certification, §8.1)")
    assessments = gov.get("assessments") or []
    if not assessments:
        e("KLM-3: at least one governance assessment is required")
    if not any(a.get("epistemic_status") == "measured" for a in assessments
               if isinstance(a, dict)):
        e("KLM-3: no deterministic (measured) assessment — model-judged "
          "findings may only enrich, never be the sole basis (§4.3)")
    policies = {p.get("id"): p for p in gov.get("policies") or [] if isinstance(p, dict)}
    if not policies:
        e("KLM-3: governance.policies is empty — findings rest on unattested norms")
    for a in assessments:
        if not isinstance(a, dict):
            continue
        pol = policies.get(a.get("policy_id"))
        if pol is None:
            continue  # KLM-0 already flags unresolvable policy_ids
        if not pol.get("source"):
            e(f"KLM-3: policy[{pol.get('id')}].source missing — the norm "
              f"itself must be attestable (§5 L5 governance provenance)")

    return errs


def validate_level4(record: dict) -> list[str]:
    """KLM-4 'Attributable' checks — every reflective finding is
    edge-traceable to its generative cause; L3 establishes at least
    execution attribution for governed behaviors (§8.3, §6.3).
    Run only on a KLM-3-clean record."""
    errs: list[str] = []
    e = errs.append
    rels = [r for r in record.get("relations", []) if isinstance(r, dict)]

    # Every assessment must be the target of an assessed_by edge whose
    # source IS its responsible object — the finding→cause chain is a
    # graph property, not a field claim.
    assessed = {(r.get("from"), r.get("to")) for r in rels if r.get("type") == "assessed_by"}
    for a in (record.get("governance") or {}).get("assessments", []):
        if not isinstance(a, dict):
            continue
        if (a.get("responsible_object"), a.get("id")) not in assessed:
            e(f"KLM-4: assessment[{a.get('id')}] lacks an assessed_by edge "
              f"from its responsible_object '{a.get('responsible_object')}'")

    # Activated procedures: every activated edge must declare at least
    # execution attribution; non-activated procedures must have none
    # (overstatement guard, §6.3).
    act_edges: dict[str, list[dict]] = {}
    for r in rels:
        if r.get("type") == "activated":
            act_edges.setdefault(r.get("from"), []).append(r)
    for pr in record.get("procedures", []):
        pid = pr.get("id")
        if pr.get("activation_status") == "activated":
            edges = act_edges.get(pid, [])
            if not edges:
                e(f"KLM-4: activated procedure[{pid}] has no activated edges")
            for r in edges:
                if r.get("attribution_level") not in ("execution_attribution", "causal_contribution"):
                    e(f"KLM-4: activated edge from [{pid}] must declare at least "
                      f"execution_attribution (got {r.get('attribution_level')!r})")
        elif pid in act_edges:
            e(f"KLM-4: procedure[{pid}] is not activated yet has activated "
              f"edges — attribution overstatement")

    # Governed behaviors instrumented: a failing claim-level finding must
    # correspond to a procedure execution touching that claim's span
    # (the behavioral response to the violation is itself attributed).
    claim_ids = {c.get("id") for c in record.get("claims", [])}
    span_of_claim = {r.get("from"): r.get("to") for r in rels if r.get("type") == "expressed_as"}
    touched = {r.get("to") for r in rels if r.get("type") == "activated"}
    for a in (record.get("governance") or {}).get("assessments", []):
        if not isinstance(a, dict) or a.get("status") != "fail":
            continue
        ro = a.get("responsible_object")
        if ro in claim_ids:
            span = span_of_claim.get(ro)
            if span not in touched:
                e(f"KLM-4: failing finding on claim[{ro}] but no procedure "
                  f"execution touches its span — governed behavior not instrumented")

    return errs


def main(argv: list[str]) -> int:
    target_level = 1
    paths: list[str] = []
    i = 0
    while i < len(argv):
        if argv[i] == "--level":
            target_level = int(argv[i + 1])
            i += 2
        else:
            paths.append(argv[i])
            i += 1
    if not paths:
        print(__doc__)
        return 1

    failed = False
    for path in paths:
        try:
            with open(path, "r", encoding="utf-8") as fh:
                record = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"FAIL  {path}: unreadable ({exc})")
            failed = True
            continue

        # Signed envelope → verify signature first (KLM-5 surface), then
        # ladder the enclosed record.
        signature_ok = None
        if isinstance(record, dict) and record.get("schema") == "klm-attestation-envelope/0.1":
            from sign_attestation import verify_envelope
            sig_errs = verify_envelope(record)
            if sig_errs:
                failed = True
                print(f"FAIL  {path} — envelope signature invalid:")
                for err in sig_errs:
                    print(f"      - {err}")
                continue
            signature_ok = True
            record = record["record"]

        errs0 = validate(record)
        if errs0:
            failed = True
            print(f"FAIL  {path} — NOT KLM-0 conformant ({len(errs0)} violation(s))")
            for err in errs0:
                print(f"      - {err}")
            continue
        errs1 = validate_level1(record)
        errs2 = validate_level2(record) if not errs1 else None
        errs3 = validate_level3(record) if (errs1 == [] and errs2 == []) else None
        errs4 = validate_level4(record) if errs3 == [] else None
        reached = 0 if errs1 else (1 if errs2 else (2 if errs3 else (3 if errs4 else 4)))
        if reached == 4 and signature_ok:
            reached = 5
        names = {0: "KLM-0 Declared", 1: "KLM-1 Traceable",
                 2: "KLM-2 Grounded", 3: "KLM-3 Reflective",
                 4: "KLM-4 Attributable", 5: "KLM-5 Verifiable"}
        n = record
        stats = (f"[{len(n.get('claims', []))} claims, {len(n.get('evidence', []))} evidence, "
                 f"{len(n.get('procedures', []))} procedures, {len(n.get('relations', []))} edges]")
        if reached >= target_level:
            print(f"PASS  {path} — {names[reached]} {stats}")
        else:
            failed = True
            gaps = errs1 if errs1 else (errs2 if errs2 else (errs3 if errs3 else (errs4 or [])))
            print(f"FAIL  {path} — {names[reached]} only; KLM-{reached + 1} gaps ({len(gaps)}):")
            for err in gaps:
                print(f"      - {err}")
    return 1 if failed else 0


def cli() -> None:
    """Console-script entry point (pip install klm-conformance)."""
    raise SystemExit(main(sys.argv[1:]))


if __name__ == "__main__":
    cli()
