# MIRAI-ID Charlson Comorbidity Definition v1

`mirai-id-cci@1` is a complete, standalone ICD-10 Charlson definition for
MIRAI-ID (Multicenter Innovative Research Alliance In Infectious Diseases).
It uses the 17 conditions, original weights and three severity suppression
relations of the [Quan et al. 2005 Table 1 algorithm](https://pubmed.ncbi.nlm.nih.gov/16224307/),
with exactly three added prefixes:

| Condition | Added prefix | Rationale |
|---|---|---|
| `aids_hiv` | B23 | The current Japanese ICD-10 B23.0, B23.1, B23.2 and B23.8 subcategories explicitly describe HIV disease. |
| `malignancy` | C86 | The current classification identifies specified T/NK-cell lymphomas. |
| `malignancy` | D45 | Polycythaemia vera was included by the historical C. koseri definition. The Japanese classification notes its malignant classification in ICD-O-3 while retaining D45 in ICD-10. |

The classification sources are the Japanese Ministry of Health, Labour and
Welfare's [infectious-disease table](https://www.mhlw.go.jp/toukei/sippei/dl/naiyou01.pdf)
and [neoplasm table](https://www.mhlw.go.jp/toukei/sippei/dl/naiyou02.pdf).
The choice to apply Charlson weights to these additional codes is a MIRAI-ID
research decision, not a validation of the extended definition's predictive
performance. `quan-2005@1` remains the immutable published-reference snapshot.

Use `definition="mirai-id-cci", version="1"` in a research run. Retain the
returned definition id/version/SHA-256 and algorithm id/version in derivation
metadata. Changing code membership, weights or suppression requires a new
definition version; changing the evaluator procedure requires a new algorithm
version. An unversioned `latest` request resolves through the package registry,
so it is convenient for exploration but should not be used for publication runs.
