"""Render the annual structural evidence matrix from the reviewed spec."""
from __future__ import annotations

from pathlib import Path

from compile_schemas import build_schema, load_json


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "spec/dpc"


def report() -> str:
    registry = load_json(SOURCE / "registry.json")
    ledger = load_json(SOURCE / "source_ledger.json")
    sources = {source["source_id"]: source for source in ledger["sources"]}
    entries = {entry["id"]: entry for entry in registry["schemas"]}
    built = {}
    lines = [
        "# OpenDPC-JP 年度別DPC構造監査表",
        "",
        "各行は診療月から選ぶ構造schema。FF1数は公式表から転記したコードとpayload位置の件数。",
        "EF17欄は意味を持つ位置（残りは予備）。証拠数はFF1 payloadとEF17の有効位置の合計で、",
        "臨床上の妥当性や提出仕様の完全検証を意味しない。資料PDFは配布物に含めない。",
        "",
        "| Schema | Data period | Structural source | Document revision | FF1 codes | Payloads | EFn EF17 | EFg EF17 | Official | Inferred | Unsupported |",
        "|---|---|---|---|---:|---:|---|---|---:|---:|---:|",
    ]
    for entry in registry["schemas"]:
        if entry["year"] is None or not entry.get("selectable_by_date", True):
            continue
        schema = build_schema(entry["id"], entries, SOURCE, built, set())
        codes = schema["ff1"]["codes"]
        payloads = sum(len(code["payloads"]) for code in codes.values())
        active = {}
        for kind in ("efn", "efg"):
            spec = schema["ef"][kind + "_ef17"]
            active[kind] = [int(index) for index, value in spec["positions"].items() if "name" in value]
        ff1_evidence = schema["definition_evidence"]["ff1"]["evidence_level"]
        ef_evidence = schema["definition_evidence"]["ef"]["evidence_level"]
        official = inferred = unsupported = 0
        for count, evidence in ((payloads, ff1_evidence), (sum(map(len, active.values())), ef_evidence)):
            if evidence.startswith("official"):
                official += count
            elif evidence == "inferred":
                inferred += count
            else:
                unsupported += count
        def label(kind):
            spec = schema["ef"][kind + "_ef17"]
            positions = active[kind]
            return f"{','.join(map(str, positions)) or 'none'} / {spec['length']}"
        primary_source_id = schema["source_ids"][0]
        primary_source = sources[primary_source_id]
        source_link = f"[{primary_source_id}]({primary_source['url']})"
        lines.append(f"| {entry['id']} | {schema['effective_from']}–{schema['effective_to']} | "
                     f"{source_link} | {schema['document_revision']} | {len(codes)} | {payloads} | {label('efn')} | {label('efg')} | "
                     f"{official} | {inferred} | {unsupported} |")
    lines += [
        "",
        "2024年4–5月は2023年度仕様、2026年4–5月は2025年度仕様を適用する。",
        "2017年4月版と7月版は、モデル化したFF1表とEF列幅が一致する。後者を訂正版として記録する。",
        "`dpc-2026-20260717` は明示IDで再現するための文書改訂profileで、診療月からは選ばない。",
        "構造表の検証は `python tools/verify_annual_source_tables.py`、resource同期は",
        "`python tools/compile_schemas.py --check` で行う。原資料のhashと役割は",
        "`spec/dpc/source_ledger.json` に記録する。",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    print(report())
