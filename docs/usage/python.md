# Python の使い方

公開 API の import 名は `open_dpc_jp` です。以下は公開候補の最小例です。

```python
from pathlib import Path
from open_dpc_jp.parsing import parse_ef, parse_ff1

ef = parse_ef(Path("EFn.txt"), source_kind="efn", dataset_year=2025)
ff1 = parse_ff1(Path("FF1.txt"), schema_id="dpc-2025-20250530")
print(ef["diagnostics"], ff1["schema"])
```

年度に複数改訂がある場合は、schema ID または有効な `dataset_date` を指定します。対応外年度を自動で既知年度と同一視しません。`allow_fallback=True` は明示した場合のみ利用し、返された warning を確認してください。

```python
from open_dpc_jp.semantics.comorbidity import calculate_charlson

result = calculate_charlson(["I21.0", "C78.0", "C34.9"], definition="quan-2005")
print(result["score"])
```

CCI は渡された診断コードだけを評価します。入力がないことは臨床的な併存疾患の不在を意味しません。研究では定義 ID・版と source hash を記録してください。方法の違いは [CCI の方法](../methods/cci.md)で説明します。
