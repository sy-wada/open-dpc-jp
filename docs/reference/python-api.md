# Python API の入口

| import | 主な用途 |
|---|---|
| `open_dpc_jp.parsing` | `parse_ef`、`parse_ff1` による構造的読込 |
| `open_dpc_jp.schemas` | `resolve_schema` と source ledger |
| `open_dpc_jp.references` | 明示的な参照 CSV の読込 |
| `open_dpc_jp.semantics.drugs` / `.procedures` | 明示的参照に基づく注釈 |
| `open_dpc_jp.semantics.comorbidity` | `calculate_charlson`、定義選択 |

parse envelope と CCI の結果は版・根拠を含みます。返り値を臨床的な確定値と混同しないでください。詳細な引数と制約は package の Python docstring、conformance fixture と [Python 使用例](../usage/python.md)を参照してください。
