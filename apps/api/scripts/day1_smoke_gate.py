from __future__ import annotations

import argparse
import json
import mimetypes
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Tuple

import requests


def _pick_files(input_dir: Path, limit: int) -> List[Path]:
    exts = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}
    files = [p for p in sorted(input_dir.rglob("*")) if p.is_file() and p.suffix.lower() in exts]
    return files[:limit]


def _pick_file_sets(input_dir: Path, limit_sets: int) -> List[List[Path]]:
    exts = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}
    grouped: Dict[Path, List[Path]] = {}
    for p in sorted(input_dir.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in exts:
            continue
        grouped.setdefault(p.parent, []).append(p)
    sets = [sorted(v) for _, v in sorted(grouped.items(), key=lambda kv: str(kv[0])) if v]
    return sets[:limit_sets]


def _build_base_headers(bearer: str = "", api_key: str = "", vercel_bypass: str = "") -> Dict[str, str]:
    headers: Dict[str, str] = {}
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    if api_key:
        headers["x-api-key"] = api_key
    if vercel_bypass:
        headers["x-vercel-protection-bypass"] = vercel_bypass
        headers["x-vercel-set-bypass-cookie"] = "true"
    return headers


def _prepare_csrf(session: requests.Session, base_url: str, base_headers: Dict[str, str], timeout: int = 30) -> str:
    paths = ("/api/auth/csrf-token", "/auth/csrf-token")
    last_err: Exception | None = None
    for p in paths:
        url = base_url.rstrip("/") + p
        try:
            resp = session.get(url, headers=base_headers, timeout=timeout)
            resp.raise_for_status()
            payload = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
            token = str(payload.get("csrf_token") or "")
            if token:
                return token
        except Exception as exc:  # pragma: no cover - fallback path handling
            last_err = exc
            continue
    raise RuntimeError(f"csrf_token_missing_from_endpoint: {last_err}")


def _post_validate(
    session: requests.Session,
    base_url: str,
    file_paths: List[Path],
    csrf_token: str,
    timeout: int = 120,
    bearer: str = "",
    api_key: str = "",
    vercel_bypass: str = "",
) -> Dict[str, Any]:
    url = base_url.rstrip("/") + "/api/validate/"
    headers = _build_base_headers(bearer=bearer, api_key=api_key, vercel_bypass=vercel_bypass)
    headers["X-CSRF-Token"] = csrf_token

    handles = []
    files_payload = []
    try:
        for idx, path in enumerate(file_paths):
            mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            f = path.open("rb")
            handles.append(f)
            files_payload.append((f"file_{idx+1}", (path.name, f, mime)))

        resp = session.post(
            url,
            files=files_payload,
            data={"userType": "exporter"},
            headers=headers,
            timeout=timeout,
        )
    finally:
        for h in handles:
            h.close()

    resp.raise_for_status()
    return resp.json()


def _coerce_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _coerce_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _append_unique_text(values: List[str], candidate: Any) -> None:
    if isinstance(candidate, (list, tuple, set)):
        for item in candidate:
            _append_unique_text(values, item)
        return
    if isinstance(candidate, dict):
        return
    text = str(candidate or "").strip()
    if text and text not in values:
        values.append(text)


def _sorted_unique_texts(values: List[str]) -> List[str]:
    return sorted({str(value).strip() for value in values if str(value or "").strip()})


def _first_text(mapping: Dict[str, Any], keys: Tuple[str, ...]) -> str:
    for key in keys:
        value = mapping.get(key)
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _document_hint(document: Dict[str, Any]) -> str:
    return _first_text(
        document,
        ("name", "filename", "document_name", "documentName", "document_type", "documentType", "id"),
    )


def _field_source_doc_hint(document: Dict[str, Any], field_name: str) -> str:
    field_details = _coerce_dict(document.get("field_details")) or _coerce_dict(document.get("fieldDetails"))
    field_entry = _coerce_dict(field_details.get(field_name))

    if not field_entry:
        artifacts = _coerce_dict(document.get("extraction_artifacts_v1"))
        field_entry = _coerce_dict(_coerce_dict(artifacts.get("field_diagnostics")).get(field_name))

    direct_hint = _first_text(
        field_entry,
        (
            "source_document",
            "source_doc",
            "document",
            "document_name",
            "documentName",
            "filename",
            "file_name",
            "fileName",
            "document_type",
            "documentType",
        ),
    )
    if direct_hint:
        return direct_hint
    return _document_hint(document)


def _merge_field_status(
    field_level_status: Dict[str, str],
    source_doc_hints: Dict[str, str],
    field_name: str,
    state: Any,
    source_hint: str,
) -> None:
    field = str(field_name or "").strip()
    normalized_state = str(state or "").strip().lower()
    if not field or not normalized_state:
        return

    priority = {
        "parse_failed": 3,
        "missing": 2,
        "found": 1,
    }
    current = field_level_status.get(field)
    if current is None or priority.get(normalized_state, 0) > priority.get(current, 0):
        field_level_status[field] = normalized_state
        if source_hint:
            source_doc_hints[field] = source_hint
    elif source_hint and field not in source_doc_hints:
        source_doc_hints[field] = source_hint


def _extract_set_diagnostics(payload: Dict[str, Any]) -> Dict[str, Any]:
    structured = _coerce_dict(payload.get("structured_result"))
    submission_eligibility = _coerce_dict(structured.get("submission_eligibility"))
    gate_result = _coerce_dict(structured.get("gate_result"))
    extraction_diagnostics = _coerce_dict(structured.get("_extraction_diagnostics"))
    day1_contract = _coerce_dict(structured.get("_day1_contract"))
    day1_relay_debug = _coerce_dict(structured.get("_day1_relay_debug"))
    day1_contract_debug = _coerce_dict(structured.get("_day1_contract_debug"))
    day1_hook_callsite_summary = _coerce_dict(structured.get("_day1_hook_callsite_summary"))
    documents = (
        _coerce_list(structured.get("documents"))
        or _coerce_list(structured.get("documents_structured"))
        or _coerce_list(payload.get("documents"))
    )

    unresolved_critical_fields: List[str] = []
    violation_reason_codes: List[str] = []
    field_level_status: Dict[str, str] = {}
    source_doc_hints: Dict[str, str] = {}

    raw_unresolved = _coerce_list(submission_eligibility.get("unresolved_critical_fields"))
    for item in raw_unresolved:
        if isinstance(item, dict):
            field_name = str(item.get("field") or item.get("name") or "").strip()
            if field_name:
                unresolved_critical_fields.append(field_name)
                direct_hint = _first_text(
                    item,
                    (
                        "source_document",
                        "source_doc",
                        "document",
                        "document_name",
                        "documentName",
                        "filename",
                        "file_name",
                        "fileName",
                        "document_type",
                        "documentType",
                    ),
                )
                if direct_hint:
                    source_doc_hints[field_name] = direct_hint
            _append_unique_text(violation_reason_codes, item.get("reason_code"))
        else:
            _append_unique_text(unresolved_critical_fields, item)

    _append_unique_text(violation_reason_codes, submission_eligibility.get("missing_reason_codes"))
    _append_unique_text(violation_reason_codes, gate_result.get("missing_reason_codes"))
    _append_unique_text(violation_reason_codes, gate_result.get("failure_reasons"))
    _append_unique_text(violation_reason_codes, extraction_diagnostics.get("failure_reasons"))

    for violation in _coerce_list(day1_contract.get("violations")):
        if isinstance(violation, dict):
            _append_unique_text(violation_reason_codes, violation.get("code"))
            _append_unique_text(violation_reason_codes, violation.get("reason_code"))

    for document in documents:
        if not isinstance(document, dict):
            continue

        _append_unique_text(violation_reason_codes, document.get("review_reasons"))
        _append_unique_text(violation_reason_codes, document.get("reviewReasons"))

        extraction_debug = _coerce_dict(document.get("extraction_debug")) or _coerce_dict(document.get("extractionDebug"))
        _append_unique_text(violation_reason_codes, extraction_debug.get("reason_codes"))

        for state_map in (
            _coerce_dict(document.get("critical_field_states")),
            _coerce_dict(document.get("criticalFieldStates")),
            _coerce_dict(extraction_debug.get("critical_field_states")),
        ):
            for field_name, state in state_map.items():
                _merge_field_status(
                    field_level_status,
                    source_doc_hints,
                    str(field_name),
                    state,
                    _field_source_doc_hint(document, str(field_name)),
                )

        artifacts = _coerce_dict(document.get("extraction_artifacts_v1"))
        field_diagnostics = _coerce_dict(artifacts.get("field_diagnostics"))
        for field_name, details in field_diagnostics.items():
            if not isinstance(details, dict):
                continue
            state = details.get("state")
            _merge_field_status(
                field_level_status,
                source_doc_hints,
                str(field_name),
                state,
                _field_source_doc_hint(document, str(field_name)),
            )
            if str(state or "").strip().lower() != "found":
                _append_unique_text(violation_reason_codes, details.get("reason_codes"))

    if not unresolved_critical_fields:
        _append_unique_text(unresolved_critical_fields, extraction_diagnostics.get("unresolved_critical_fields"))

    for field_name, state in field_level_status.items():
        if state != "found":
            _append_unique_text(unresolved_critical_fields, field_name)

    relay_surfaces = _coerce_dict(day1_relay_debug.get("surfaces"))
    runtime_presence_by_surface: Dict[str, Dict[str, int]] = {}
    hook_presence_by_surface: Dict[str, Dict[str, int]] = {}
    for surface_name, entries in relay_surfaces.items():
        entry_list = _coerce_list(entries)
        runtime_presence_by_surface[str(surface_name)] = {
            "docs": len(entry_list),
            "runtime_present": sum(1 for item in entry_list if isinstance(item, dict) and item.get("runtime_present")),
        }
        hook_presence_by_surface[str(surface_name)] = {
            "callsite_reached": sum(1 for item in entry_list if isinstance(item, dict) and item.get("hook_callsite_reached")),
            "invoked": sum(1 for item in entry_list if isinstance(item, dict) and item.get("hook_invoked")),
            "attached": sum(1 for item in entry_list if isinstance(item, dict) and item.get("hook_attached")),
            "runtime_present": sum(1 for item in entry_list if isinstance(item, dict) and item.get("hook_runtime_present")),
        }

    contract_documents_source = str(day1_contract_debug.get("documents_source") or "")
    contract_docs = _coerce_list(day1_contract_debug.get("per_doc"))
    contract_doc_runtime_missing = [
        str(doc.get("filename") or "")
        for doc in contract_docs
        if isinstance(doc, dict) and not bool(doc.get("runtime_present"))
    ]
    contract_doc_thresholds = {
        str(doc.get("filename") or ""): int(doc.get("threshold") or 0)
        for doc in contract_docs
        if isinstance(doc, dict) and str(doc.get("filename") or "").strip()
    }
    contract_doc_fallback_stages = {
        str(doc.get("filename") or ""): str(doc.get("fallback_stage") or "")
        for doc in contract_docs
        if isinstance(doc, dict) and str(doc.get("filename") or "").strip()
    }

    contract_violation_reason_codes: List[str] = []
    for violation in _coerce_list(day1_contract.get("violations")):
        if isinstance(violation, dict):
            _append_unique_text(contract_violation_reason_codes, violation.get("code"))

    field_diagnostic_reason_codes = [
        code
        for code in _sorted_unique_texts(violation_reason_codes)
        if code not in _sorted_unique_texts(contract_violation_reason_codes)
    ]

    return {
        "unresolved_critical_fields": _sorted_unique_texts(unresolved_critical_fields),
        "violation_reason_codes": _sorted_unique_texts(violation_reason_codes),
        "field_level_status": {field: field_level_status[field] for field in sorted(field_level_status)},
        "critical_field_source_doc_hints": {
            field: source_doc_hints[field]
            for field in sorted(source_doc_hints)
            if field in field_level_status or field in source_doc_hints
        },
        "contract_documents_source": contract_documents_source,
        "runtime_presence_by_surface": runtime_presence_by_surface,
        "hook_presence_by_surface": hook_presence_by_surface,
        "contract_doc_runtime_missing": _sorted_unique_texts(contract_doc_runtime_missing),
        "day1_hook_callsite_summary": day1_hook_callsite_summary,
        "contract_doc_thresholds": contract_doc_thresholds,
        "contract_doc_fallback_stages": contract_doc_fallback_stages,
        "contract_violation_reason_codes": _sorted_unique_texts(contract_violation_reason_codes),
        "field_diagnostic_reason_codes": field_diagnostic_reason_codes,
    }


def _build_diagnostics_aggregate(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    critical_fields = Counter()
    reason_codes = Counter()

    for result in results:
        if not isinstance(result, dict):
            continue
        for field_name in _sorted_unique_texts(_coerce_list(result.get("unresolved_critical_fields"))):
            critical_fields[field_name] += 1
        for reason_code in _sorted_unique_texts(_coerce_list(result.get("violation_reason_codes"))):
            reason_codes[reason_code] += 1

    return {
        "top_critical_fields_frequency": [
            {"field": field_name, "count": count}
            for field_name, count in sorted(critical_fields.items(), key=lambda item: (-item[1], item[0]))
        ],
        "top_reason_codes_frequency": [
            {"reason_code": reason_code, "count": count}
            for reason_code, count in sorted(reason_codes.items(), key=lambda item: (-item[1], item[0]))
        ],
    }


def _extract_gate_metrics(payload: Dict[str, Any]) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
    structured = payload.get("structured_result") if isinstance(payload.get("structured_result"), dict) else {}
    contract = structured.get("_day1_contract") if isinstance(structured.get("_day1_contract"), dict) else {}
    metrics = structured.get("_day1_metrics") if isinstance(structured.get("_day1_metrics"), dict) else {}

    status = str(contract.get("status") or "")
    if not status and structured:
        validation_status = str(structured.get("validation_status") or "").lower()
        can_submit = bool(((structured.get("submission_eligibility") or {}).get("can_submit")) if isinstance(structured.get("submission_eligibility"), dict) else False)
        if validation_status in {"blocked", "review", "partial"}:
            status = "review"
        elif validation_status in {"ok", "pass", "passed", "ready"} or can_submit:
            status = "pass"

    if not status:
        status = "unknown"

    if not contract and structured:
        # fallback pseudo-contract from current live schema
        contract = {
            "version": "fallback-live-schema",
            "status": status,
            "violations": (structured.get("submission_eligibility") or {}).get("unresolved_critical_fields") or [],
        }

    if not metrics:
        metrics = {
            "ret_no_hit": 0,
            "ret_low_relevance": 0,
        }

    return status, contract, metrics


def run_smoke(
    base_url: str,
    input_dir: Path,
    limit: int,
    bearer: str = "",
    api_key: str = "",
    vercel_bypass: str = "",
    bundle_by_dir: bool = True,
) -> Dict[str, Any]:
    if bundle_by_dir:
        file_sets = _pick_file_sets(input_dir, limit_sets=limit)
        if not file_sets:
            raise RuntimeError(f"No document sets found in {input_dir}")
    else:
        files = _pick_files(input_dir, limit)
        if not files:
            raise RuntimeError(f"No documents found in {input_dir}")
        file_sets = [[f] for f in files]

    results = []
    contract_counts = {"pass": 0, "review": 0, "unknown": 0}
    total_ret_no_hit = 0
    total_ret_low = 0
    total_violations = 0

    session = requests.Session()
    base_headers = _build_base_headers(bearer=bearer, api_key=api_key, vercel_bypass=vercel_bypass)
    csrf_token = _prepare_csrf(session, base_url, base_headers)

    for file_set in file_sets:
        label = file_set[0].parent.name if len(file_set) > 1 else file_set[0].name
        try:
            payload = _post_validate(
                session,
                base_url,
                file_set,
                csrf_token,
                bearer=bearer,
                api_key=api_key,
                vercel_bypass=vercel_bypass,
            )
            status, contract, metrics = _extract_gate_metrics(payload)
            diagnostics = _extract_set_diagnostics(payload)
            contract_counts[status] = contract_counts.get(status, 0) + 1
            total_ret_no_hit += int(metrics.get("ret_no_hit") or 0)
            total_ret_low += int(metrics.get("ret_low_relevance") or 0)
            total_violations += len(contract.get("violations") or [])
            results.append({
                "set": label,
                "files": [p.name for p in file_set],
                "ok": True,
                "contract_status": status,
                "violations": len(contract.get("violations") or []),
                "ret_no_hit": int(metrics.get("ret_no_hit") or 0),
                "ret_low_relevance": int(metrics.get("ret_low_relevance") or 0),
                "unresolved_critical_fields": diagnostics["unresolved_critical_fields"],
                "violation_reason_codes": diagnostics["violation_reason_codes"],
                "field_level_status": diagnostics["field_level_status"],
                "critical_field_source_doc_hints": diagnostics["critical_field_source_doc_hints"],
                "contract_documents_source": diagnostics["contract_documents_source"],
                "runtime_presence_by_surface": diagnostics["runtime_presence_by_surface"],
                "hook_presence_by_surface": diagnostics["hook_presence_by_surface"],
                "contract_doc_runtime_missing": diagnostics["contract_doc_runtime_missing"],
                "day1_hook_callsite_summary": diagnostics["day1_hook_callsite_summary"],
                "contract_doc_thresholds": diagnostics["contract_doc_thresholds"],
                "contract_doc_fallback_stages": diagnostics["contract_doc_fallback_stages"],
                "contract_violation_reason_codes": diagnostics["contract_violation_reason_codes"],
                "field_diagnostic_reason_codes": diagnostics["field_diagnostic_reason_codes"],
            })
        except Exception as e:
            results.append({
                "set": label,
                "files": [p.name for p in file_set],
                "ok": False,
                "error": str(e),
                "contract_status": "unknown",
                "unresolved_critical_fields": [],
                "violation_reason_codes": [],
                "field_level_status": {},
                "critical_field_source_doc_hints": {},
                "contract_documents_source": "",
                "runtime_presence_by_surface": {},
                "hook_presence_by_surface": {},
                "contract_doc_runtime_missing": [],
                "day1_hook_callsite_summary": {},
                "contract_doc_thresholds": {},
                "contract_doc_fallback_stages": {},
                "contract_violation_reason_codes": [],
                "field_diagnostic_reason_codes": [],
            })
            contract_counts["unknown"] = contract_counts.get("unknown", 0) + 1

    processed = len(results)
    hard_failures = sum(1 for r in results if not r.get("ok"))

    gate_pass = hard_failures == 0 and contract_counts.get("unknown", 0) == 0

    return {
        "base_url": base_url,
        "input_dir": str(input_dir),
        "processed": processed,
        "contract_counts": contract_counts,
        "total_violations": total_violations,
        "ret_no_hit_total": total_ret_no_hit,
        "ret_low_relevance_total": total_ret_low,
        "hard_failures": hard_failures,
        "gate_pass": gate_pass,
        "diagnostics_aggregate": _build_diagnostics_aggregate(results),
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Day-1 20-doc staging smoke gate")
    parser.add_argument("--base-url", required=True, help="API base url, e.g. http://localhost:8000")
    parser.add_argument("--input-dir", required=True, help="Directory with docs (.pdf/.png/...) for smoke")
    parser.add_argument("--limit", type=int, default=20, help="Number of sets/docs to run (default: 20)")
    parser.add_argument("--no-bundle-by-dir", action="store_true", help="Send one file per request instead of folder sets")
    parser.add_argument("--bearer", default="", help="Bearer token for Authorization header")
    parser.add_argument("--api-key", default="", help="Optional x-api-key header")
    parser.add_argument("--vercel-bypass", default="", help="Optional Vercel deployment protection bypass token")
    parser.add_argument("--out", default="day1_smoke_report.json", help="Output report file")
    args = parser.parse_args()

    report = run_smoke(
        args.base_url,
        Path(args.input_dir),
        args.limit,
        bearer=args.bearer,
        api_key=args.api_key,
        vercel_bypass=args.vercel_bypass,
        bundle_by_dir=not args.no_bundle_by_dir,
    )
    out_path = Path(args.out)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps({
        "processed": report["processed"],
        "gate_pass": report["gate_pass"],
        "contract_counts": report["contract_counts"],
        "total_violations": report["total_violations"],
        "ret_no_hit_total": report["ret_no_hit_total"],
        "ret_low_relevance_total": report["ret_low_relevance_total"],
        "diagnostics_aggregate": report["diagnostics_aggregate"],
        "out": str(out_path),
    }, indent=2))


if __name__ == "__main__":
    main()
