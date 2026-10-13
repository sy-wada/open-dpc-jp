# MIRAI-ID Charlson Comorbidity Definition v1

## 2026-10-13 pre-study revision

MIRAI-ID (Multicenter Innovative Research Alliance In Infectious Diseases) uses
Quan 2005's 17 conditions, original weights and three severity suppression
relations as its baseline. It is a distinct, non-standard research definition.
The developing v1 was revised in place at the maintainer's explicit direction,
before any research run used it. The fixed `quan-2005@1` reference is unchanged.

| Extension | Assignment | Basis |
|---|---|---|
| B23 | AIDS/HIV | Current Japanese HIV disease categories |
| C86 / D45 | Malignancy | T/NK lymphoma; polycythaemia vera retained from the study definition |
| Exact E10–E14 | Diabetes, minimum 1 point | Diabetes is identified; complication status is unspecified |
| Exact K70 | Liver disease, minimum 1 point | All subcategories are covered across mild/severe liver conditions; severity is unspecified |
| Exact I85 | Moderate/severe liver disease, 3 points | Both current Japanese subcategories are in the baseline condition |
| Exact Z49 | Renal disease, 2 points | All subcategories are in the baseline condition; dialysis modality is unspecified |
| I74 prefix | Peripheral vascular disease, 1 point | Arterial embolism/thrombosis; MIRAI extension including acute arterial insufficiency |
| I983 prefix | Moderate/severe liver disease, 3 points | Current Japanese classification separates bleeding oesophageal varices in diseases classified elsewhere |

Exact categories never substitute E119 for E11 or K709 for K70. A detailed
complicated-diabetes or severe-liver code retains its own condition and
suppresses the minimum-weight condition. Lower-weight condition keys on coarse
input are **minimum assignments**, not evidence of no complications or mild
disease. Z49 does not by itself establish hemodialysis in a study-specific form.

The [43-category screening](CCI-CATEGORY-SCREENING.md) documents the eight
accepted categories and 35 mixed categories. The latter produce related,
classification-insufficient evidence, not positive membership. Specific
excluded descendants remain excluded. Classification uncertainty and temporal
eligibility are distinct.

## Sources and interpretation

- [Quan et al. 2005 Table 1](https://pubmed.ncbi.nlm.nih.gov/16224307/).
- Japanese MHLW ICD-10 (2013) [classification](https://www.mhlw.go.jp/toukei/sippei/index.html):
  [infection](https://www.mhlw.go.jp/toukei/sippei/dl/naiyou01.pdf),
  [neoplasms](https://www.mhlw.go.jp/toukei/sippei/dl/naiyou02.pdf),
  [diabetes](https://www.mhlw.go.jp/toukei/sippei/dl/naiyou04.pdf),
  [circulation](https://www.mhlw.go.jp/toukei/sippei/dl/naiyou09.pdf),
  [liver](https://www.mhlw.go.jp/toukei/sippei/dl/naiyou11.pdf),
  [dialysis](https://www.mhlw.go.jp/toukei/sippei/dl/naiyou21.pdf).
- [Clinical trial protocol, Appendix H, CCI rules](https://cdn.clinicaltrials.gov/large-docs/00/NCT00553800/Prot_SAP_000.pdf)
  includes acute arterial insufficiency in peripheral vascular disease.
  This supports the extension's clinical interpretation, not a claim that
  Quan includes I74 or that MIRAI's predictive performance is validated.

The I74 category excludes coronary, cerebral, pulmonary, mesenteric, renal and
retinal arterial embolism/thrombosis into other ICD categories. Its .0/.1
aortic, .2–.4 limb, .5 iliac and .8/.9 other/unspecified arterial subcategories
are all covered by the MIRAI extension. Venous thrombosis is not added.

Applying Charlson weights to the extensions and unknown-severity minimums is
a research policy. Classification sources do not establish predictive validity.

## Identity, compatibility and reproduction

Private package 0.3.1 / public package 0.1.1 contain revised `mirai-id-cci@1`.
Retain the returned definition id/version/**SHA-256**, package version and
algorithm id/version. Definition version alone does not distinguish this
pre-study revision.

- Previous v1 canonical source SHA-256: `462fe404950ebe51e42c054d3819ce78f4aec34d9191050b9f5735817dd23e45`.
- Revised v1 canonical source SHA-256: `7bea9ddf882a4c941a6a9144191e9faa58f49bb6d7b92a832aec964c3c124dee`.
- Revised definition uses `charlson-prefix-hierarchy@2`.
- Quan and archived prefix-only v1 use algorithm 1.

The previous JSON is shipped at
`open_dpc/semantics/comorbidity/definitions/archive/mirai-id-cci-v1-20260923.json`
and can be evaluated through the existing external Path API:

```python
from importlib.resources import files
from open_dpc_jp.semantics.comorbidity import calculate_charlson
old = files("open_dpc.semantics.comorbidity").joinpath(
    "definitions/archive/mirai-id-cci-v1-20260923.json")
previous = calculate_charlson(["E11", "I745"], definition=old, version="1")
current = calculate_charlson(["E11", "I745"], definition="mirai-id-cci", version="1")
assert previous["score"] == 0 and current["score"] == 2
```

The package computes supplied observations only. Curation acceptance, dates,
suspicion policy, observation completeness and clinical exports belong to the
caller. Candidate refresh is not permission to rewrite confirmed values.
Future research revisions should receive a new definition version; this
explicit pre-study exception is not a policy of silently replacing fixed
research snapshots.
