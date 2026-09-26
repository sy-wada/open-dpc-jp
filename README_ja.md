[English README](README.md)

# Open DPC JP

**Open Diagnosis Procedure Combination for Japan** は、日本の DPC FF1/EF データを年度・改訂別 profile に基づき構造的に読み込む Python ライブラリです。版付き Charlson Comorbidity Index 定義も提供します。公開初版は `0.1.0` です。

## 範囲

core の入口は library API です。DPC 抽出 script は同じ repository の別 utility として公開します。ブラウザ専用 Patient List Generator は抽出用 CSV を作成します。臨床患者データ、公式マスタ、CaseCurator の研究別規則・保存・REDCap export は含みません。構造的読込は DPC 提出や臨床妥当性の完全な検証ではありません。

## 導入

Python 3.12 以降が必要です。

```bash
python -m pip install open-dpc-jp
```

## 最小例

```python
from pathlib import Path
from open_dpc_jp.parsing import parse_ef, parse_ff1

ef = parse_ef(Path("EFn.txt"), source_kind="efn", dataset_year=2025)
ff1 = parse_ff1(Path("FF1.txt"), schema_id="dpc-2025-20250530")
print(ef["diagnostics"], ff1["schema"])
```

## 対応データと文書

2014–2026 年の構造的 profile を収録し、必要な年度は改訂を区別します。出典と制約は `spec/dpc/source_ledger.json` に記録しています。使い方、方法、入力仕様、抽出、Patient List CSV 契約は[日本語ドキュメント](https://open-dpc-jp.pages.dev/)を参照してください。[ドキュメントの原稿](docs/index.md)も repository で公開しています。

## ライセンスと引用

project-owned code は [MIT](LICENSE) で提供します。適用範囲と第三者資料は [NOTICE](NOTICE.md) を参照してください。第三者の論文、公式 DPC データ、マスタを再ライセンスしません。引用情報は [CITATION.cff](CITATION.cff) を参照し、必要に応じて原著と DPC 仕様も引用してください。
