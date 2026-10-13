# Python API の入口

| import | 主な用途 |
|---|---|
| `open_dpc_jp.parsing` | `parse_ef`、`parse_ff1` による構造的読込 |
| `open_dpc_jp.schemas` | `resolve_schema` と source ledger |
| `open_dpc_jp.references` | 明示的な参照 CSV の読込 |
| `open_dpc_jp.semantics.drugs` / `.procedures` | 明示的参照に基づく注釈 |
| `open_dpc_jp.semantics.comorbidity` | `calculate_charlson`、定義選択 |

parse envelope と CCI の結果は版・根拠を含みます。返り値を臨床的な確定値と混同しないでください。詳細な引数と制約は package の Python docstring、conformance fixture と [Python 使用例](../usage/python.md)を参照してください。

公開0.1.1の改訂MIRAI-ID v1はalgorithm 2です。`conditions[*].evidence[*]`に
`match_type`（`prefix` / `exact_category`）、最低点の根拠には任意の
`severity_status=unspecified`と`scoring_basis=minimum_weight`を追加します。
任意の`category_evidence`は、`record_index`・元`icd10`・`possible_conditions`・
`status=insufficient_specificity`を返します。関連カテゴリーは陽性conditionではありません。
構文上の`input_status=resolved`も臨床分類の確定を意味しません。分類不足・最低点の
`warnings`と併せて利用してください。標準Quan・改訂前の保存定義の結果は従来形を保持します。
