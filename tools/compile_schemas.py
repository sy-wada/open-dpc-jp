"""Compile reviewed base/deltas. --check compares without modifying resources."""
import argparse
from copy import deepcopy
import json
from pathlib import Path


def encode(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def deep_merge(base, override):
    """Merge metadata overrides without duplicating the annual payload tables."""
    if not isinstance(base, dict) or not isinstance(override, dict):
        return deepcopy(override)
    result = deepcopy(base)
    for key, value in override.items():
        result[key] = deep_merge(result[key], value) if key in result else deepcopy(value)
    return result


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def build_schema(entry_id, entries, source, built, building):
    if entry_id in built:
        return deepcopy(built[entry_id])
    if entry_id in building:
        raise ValueError(f"cyclic_schema_reference: {entry_id}")
    entry = entries[entry_id]
    building.add(entry_id)
    if "base" in entry:
        source_doc = load_json(source / entry["base"])
        if "extends" in source_doc:
            parent_ref = source_doc["extends"]
            if parent_ref in entries:
                schema = build_schema(parent_ref, entries, source, built, building)
            else:
                schema = load_json(source / parent_ref)
            schema = deep_merge(schema, source_doc.get("overrides", {}))
        else:
            schema = source_doc
    else:
        delta = load_json(source / entry["delta"])
        schema = build_schema(delta["base"], entries, source, built, building)
        for change in delta["changes"]:
            parent = schema
            for key in change["path"][:-1]:
                parent = parent[key]
            key = change["path"][-1]
            if change["op"] == "remove":
                del parent[key]
            elif change["op"] == "set":
                parent[key] = deepcopy(change["value"])
            else:
                raise ValueError("invalid_delta_operation")
        schema = deep_merge(schema, {key: value for key, value in delta.items() if key not in {"base", "changes"}})
    schema = deep_merge(schema, entry.get("overrides", {}))
    if schema.get("id") != entry_id:
        raise ValueError(f"schema_id_mismatch: {entry_id}")
    built[entry_id] = deepcopy(schema)
    building.remove(entry_id)
    return deepcopy(schema)


def validate_schema(schema, source_ids):
    schema_id = schema["id"]
    for source_id in schema.get("source_ids", []):
        if source_id not in source_ids:
            raise ValueError(f"unknown_source_id: {source_id}")
    for evidence in schema.get("definition_evidence", {}).values():
        for source_id in evidence.get("source_ids", []):
            if source_id not in source_ids:
                raise ValueError(f"unknown_evidence_source_id: {source_id}")
    ef = schema["ef"]
    if len(ef["columns"]) != len(ef["widths"]):
        raise ValueError(f"invalid_ef_layout: {schema_id}")
    for key in ("source_columns", "outpatient_columns", "outpatient_source_columns"):
        if key in ef and len(ef[key]) != len(ef["widths"]):
            raise ValueError(f"invalid_ef_layout: {schema_id}: {key}")
    if schema.get("year") is None:
        return
    start = schema["effective_from"]
    if schema.get("data_effective_from", start) != start:
        raise ValueError(f"data_period_mismatch: {schema_id}")
    if schema.get("data_effective_to", schema["effective_to"]) != schema["effective_to"]:
        raise ValueError(f"data_period_mismatch: {schema_id}")
    coverage = schema.get("source_coverage", {}).get("ff1_payload_pdf_pages", {})
    ff1_evidence = schema.get("definition_evidence", {}).get("ff1", {})
    ef_evidence = schema.get("definition_evidence", {}).get("ef", {})
    if ef_evidence.get("evidence_level") in {"official_table", "official_applicability"}:
        source_coverage = schema.get("source_coverage", {})
        if not all((source_coverage.get("efn_layout_pdf_page"),
                    source_coverage.get("efg_layout_pdf_page"),
                    source_coverage.get("efn_flags_pdf_pages"),
                    source_coverage.get("efg_flags_pdf_page"))):
            raise ValueError(f"missing_ef_source_page: {schema_id}")
    for code, definition in schema["ff1"]["codes"].items():
        version = definition["version"]
        if version > start:
            raise ValueError(f"future_ff1_code_version: {schema_id}: {code}")
        if ff1_evidence.get("evidence_level") in {"official_table", "official_applicability"} and not coverage.get(code):
            raise ValueError(f"missing_ff1_source_page: {schema_id}: {code}")
    for kind in ("efn", "efg"):
        positional = ef.get(f"{kind}_ef17")
        if not positional:
            raise ValueError(f"missing_ef17_definition: {schema_id}: {kind}")
        length = positional.get("length")
        if length is None:
            if positional.get("positions") or schema["definition_evidence"]["ef"]["evidence_level"] != "unsupported":
                raise ValueError(f"invalid_unsupported_ef17: {schema_id}: {kind}")
            continue
        positions = positional.get("positions", {})
        if set(positions) != {str(i) for i in range(1, length + 1)}:
            raise ValueError(f"incomplete_ef17_positions: {schema_id}: {kind}")
        for position, definition in positions.items():
            if ("name" in definition) == bool(definition.get("reserved")):
                raise ValueError(f"ambiguous_ef17_position: {schema_id}: {kind}: {position}")


def validate_inference_graph(compiled):
    graph = {schema_id: set() for schema_id in compiled}
    for schema_id, schema in compiled.items():
        for evidence in schema.get("definition_evidence", {}).values():
            graph[schema_id].update(evidence.get("inferred_from", []))
        for parent in graph[schema_id]:
            if parent not in graph:
                raise ValueError(f"unknown_inference_reference: {schema_id}: {parent}")
    active, done = set(), set()
    def visit(node):
        if node in active:
            raise ValueError(f"cyclic_inference_reference: {node}")
        if node in done:
            return
        active.add(node)
        for parent in graph[node]:
            visit(parent)
        active.remove(node)
        done.add(node)
    for schema_id in graph:
        visit(schema_id)


def compile_all(root: Path, *, check: bool = False):
    source = root / "spec/dpc"
    target = root / "src/open_dpc/schemas/compiled"
    registry = load_json(source / "registry.json")
    entries = {entry["id"]: entry for entry in registry["schemas"]}
    ledger = load_json(source / "source_ledger.json")
    source_ids = {item["source_id"] for item in ledger["sources"]}
    compiled = {}
    outputs = {}
    for entry in registry["schemas"]:
        schema = build_schema(entry["id"], entries, source, compiled, set())
        if entry["year"] is not None and any(
            schema.get(key) != entry.get(key) for key in ("effective_from", "effective_to")
        ):
            raise ValueError(f"registry_period_mismatch: {entry['id']}")
        validate_schema(schema, source_ids)
        outputs[target / (entry["id"] + ".json")] = encode(schema)
    validate_inference_graph(compiled)
    outputs[target / "registry.json"] = encode(registry)
    outputs[target / "source_ledger.json"] = encode(ledger)
    for path in (root / "spec/semantics").glob("*.json"):
        outputs[root / "src/open_dpc/semantics/comorbidity/definitions" / path.name] = path.read_bytes()
    for path, data in outputs.items():
        if check:
            if not path.is_file() or path.read_bytes() != data:
                raise ValueError(f"compiled_resource_out_of_date: {path.name}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    return len(outputs)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    print(f"{compile_all(Path(__file__).resolve().parents[1], check=args.check)} resources verified" if args.check else f"{compile_all(Path(__file__).resolve().parents[1])} resources compiled")
