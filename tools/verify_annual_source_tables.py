"""Compare annual structural FF1 and EF tables with local official PDF audit copies.

PDFs are deliberately excluded from the package. Install pdfplumber only in the
audit environment, then run this tool from the package checkout.
"""
from __future__ import annotations

import hashlib
import argparse
import json
from pathlib import Path
import re

import pdfplumber


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "spec/dpc"
PDF_DIR = ROOT / "audit-sources/dpc"

# The chosen full specifications and their FF1/EF pages were checked against
# the source ledger. Short change histories are intentionally not used here.
SOURCES = {
    2014: ("2014-full", "dpc-2014-20140501", 145, 150),
    2015: ("2015-20150402", "dpc-2015-20150402", 145, 150),
    2016: ("2016-20160401", "dpc-2016-20160401", 162, 167),
    2017: ("2017-full", "dpc-2017-20170401", 162, 167),
    2018: ("2018-20180406", "dpc-2018-20180406", 173, 178),
    2019: ("2019-20190401", "dpc-2019-20190401", 170, 176),
    2020: ("2020-20200330", "dpc-2020-20200330", 176, 182),
    2021: ("2021-20210401", "dpc-2021-20210401", 174, 180),
    2022: ("2022-20220401", "dpc-2022-20220401", 187, 194),
    2023: ("2023-20230401", "dpc-2023-20230401", 182, 189),
    2024: ("2024-20240401", "dpc-2024-20240601", 206, 213),
    2025: ("2025-20250530", "dpc-2025-20250530", 200, 207),
    2026: ("2026-20260325", "dpc-2026-20260601", 207, 214),
}

EF17_TERMS = {
    "fee_for_service_inclusive_flag": "出来高・包括フラグ",
    "discharge_prescription_flag": "退院時処方区分",
    "inclusive_item_flag": "入院料包括項目区分",
    "brought_in_drug_flag": "持参薬区分",
    "brought_in_prescriber_flag": "持参薬処方区分",
    "dpc_applicability_flag": "DPC適用区分",
    "basic_lab_xray_inclusive_flag": "基本的検体検査実施料",
    "outside_prescription_flag": "院外処方区分",
    "generic_prescription_flag": "一般名処方区分",
    "sex_code": "性別",
    "outcome_code": "転帰区分",
    "main_disease_flag": "主傷病",
    "inclusive_management_flag": "医学管理料等包括項目区分",
    "refill_prescription_flag": "リフィル処方箋区分",
}
EF17_NUMERALS = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫"


def _clean(value: str | None) -> str:
    return re.sub(r"\s", "", value or "")


def _source_codes(pdf):
    codes, pages = {}, {}
    current = None
    for page_index in range(15, min(45, len(pdf.pages))):
        page = pdf.pages[page_index]
        for table in page.extract_tables():
            if not any(re.fullmatch(r"[A-Z][A-Z0-9]{6}", _clean(cell)) for row in table for cell in row):
                continue
            for row in table:
                if len(row) not in (8, 9):
                    continue
                code = _clean(row[0])
                if re.fullmatch(r"[A-Z][A-Z0-9]{6}", code):
                    if code in codes:
                        raise ValueError(f"duplicate FF1 code on PDF page {page_index + 1}: {code}")
                    current = code
                    codes[code] = {}
                    pages[code] = page_index + 1
                number = _clean(row[5] if len(row) == 9 else row[4])
                if current and number.isdigit():
                    content = row[-1] or ""
                    codes[current][number] = {
                        "name": _clean(row[-2]),
                        "type": "date" if "YYYYMMDD" in content else "string",
                    }
    return codes, pages


def _layout(pdf, page_number):
    table = next((table for table in pdf.pages[page_number - 1].extract_tables()
                  if len(table) == 31 and len(table[0]) == 9), None)
    if table is None:
        raise ValueError(f"missing EF layout on PDF page {page_number}")
    widths, names = [], []
    for number, row in enumerate(table, 1):
        if _clean(row[0]) not in {f"EF-{number}", f"EE-{number}"}:
            raise ValueError(f"EF column order mismatch on PDF page {page_number}: {number}")
        widths.append(int(_clean(row[3])))
        names.append(_clean(row[2]))
    return widths, names


def _verify_ef17(pdf, schema, kind, year):
    coverage = schema["source_coverage"]
    pages = (coverage["efn_flags_pdf_pages"] if kind == "efn"
             else coverage.get("efg_flags_pdf_pages", [coverage["efg_flags_pdf_page"]]))
    text = _clean("".join(pdf.pages[page - 1].extract_text() or "" for page in pages))
    positions = schema["ef"][kind + "_ef17"]["positions"]
    for position, definition in positions.items():
        if "name" not in definition:
            continue
        name = definition["name"]
        term = EF17_TERMS[name]
        marker = "" if year <= 2015 else EF17_NUMERALS[int(position) - 1]
        if marker + term not in text:
            raise ValueError(f"ef17_meaning_mismatch: {year}: {kind}: {position}: {name}")


def verify(years=None):
    from compile_schemas import build_schema, load_json

    registry = load_json(SPEC / "registry.json")
    entries = {entry["id"]: entry for entry in registry["schemas"]}
    ledger = load_json(SPEC / "source_ledger.json")
    by_id = {item["source_id"]: item for item in ledger["sources"]}
    built = {}
    for year, (stem, schema_id, efn_page, efg_page) in SOURCES.items():
        if years is not None and year not in years:
            continue
        pdf_path = PDF_DIR / f"{stem}.pdf"
        schema = build_schema(schema_id, entries, SPEC, built, set())
        source_id = schema["source_ids"][0]
        ledger_entry = by_id[source_id]
        digest = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
        if digest != ledger_entry["sha256"]:
            raise ValueError(f"source_hash_mismatch: {year}")
        with pdfplumber.open(pdf_path) as pdf:
            source_codes, pages = _source_codes(pdf)
            actual_codes = schema["ff1"]["codes"]
            if set(source_codes) != set(actual_codes):
                raise ValueError(f"ff1_code_set_mismatch: {year}: {sorted(set(source_codes) ^ set(actual_codes))}")
            for code, payloads in source_codes.items():
                actual_payloads = {number: {key: value for key, value in item.items() if key in {"name", "type"}}
                                   for number, item in actual_codes[code]["payloads"].items()}
                if payloads != actual_payloads:
                    raise ValueError(f"ff1_payload_mismatch: {year}: {code}")
            if pages != schema["source_coverage"]["ff1_payload_pdf_pages"]:
                raise ValueError(f"ff1_page_mismatch: {year}")
            for kind, page in (("efn", efn_page), ("efg", efg_page)):
                widths, names = _layout(pdf, page)
                if widths != schema["ef"]["widths"]:
                    raise ValueError(f"ef_width_mismatch: {year}: PDF page {page}")
                source_columns = schema["ef"]["source_columns" if kind == "efn" else "outpatient_source_columns"]
                if names != [_clean(name) for name in source_columns]:
                    raise ValueError(f"ef_column_name_mismatch: {year}: PDF page {page}")
                _verify_ef17(pdf, schema, kind, year)
        print(f"{year}: {len(source_codes)} FF1 codes, {sum(map(len, source_codes.values()))} payloads, 31 EF column names/widths and EF17 positions verified")

    if years is None or 2017 in years:
        april_path = PDF_DIR / "2017-april-full.pdf"
        april_source = by_id["dpc-2017-full-20170406"]
        if hashlib.sha256(april_path.read_bytes()).hexdigest() != april_source["sha256"]:
            raise ValueError("source_hash_mismatch: 2017 April revision")
        july_path = PDF_DIR / "2017-full.pdf"
        profile = build_schema("dpc-2017-20170401", entries, SPEC, built, set())
        with pdfplumber.open(april_path) as april, pdfplumber.open(july_path) as july:
            april_codes, april_pages = _source_codes(april)
            july_codes, july_pages = _source_codes(july)
            if april_codes != july_codes or april_pages != july_pages:
                raise ValueError("2017_april_july_ff1_structural_difference")
            for page in (162, 167):
                if _layout(april, page) != _layout(july, page):
                    raise ValueError(f"2017_april_july_ef_width_difference: {page}")
            for kind in ("efn", "efg"):
                _verify_ef17(april, profile, kind, 2017)
        print("2017 April/July documents: modeled FF1 tables and EF column names/widths match")

    if years is None or 2026 in years:
        july_path = PDF_DIR / "2026-20260717.pdf"
        july_source = by_id["dpc-2026-20260717"]
        if hashlib.sha256(july_path.read_bytes()).hexdigest() != july_source["sha256"]:
            raise ValueError("source_hash_mismatch: 2026 July revision")
        june = build_schema("dpc-2026-20260601", entries, SPEC, built, set())
        with pdfplumber.open(july_path) as pdf:
            july_codes, july_pages = _source_codes(pdf)
            for code, definition in june["ff1"]["codes"].items():
                actual = {number: {key: value for key, value in payload.items() if key in {"name", "type"}}
                          for number, payload in definition["payloads"].items()}
                if july_codes.get(code) != actual:
                    raise ValueError(f"july_structural_difference: {code}")
            if set(july_codes) != set(june["ff1"]["codes"]):
                raise ValueError("july_code_set_difference")
            for page in (207, 214):
                if _layout(pdf, page) != (june["ef"]["widths"],
                                          [_clean(name) for name in june["ef"]["source_columns" if page == 207 else "outpatient_source_columns"]]):
                    raise ValueError(f"july_ef_width_difference: {page}")
            for kind in ("efn", "efg"):
                _verify_ef17(pdf, june, kind, 2026)
        print("2026 July document: FF1 code/payload structure and EF column names/widths match the June schema")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, action="append", choices=sorted(SOURCES))
    args = parser.parse_args()
    verify(set(args.year) if args.year else None)
