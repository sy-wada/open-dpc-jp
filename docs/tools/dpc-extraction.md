# DPC 抽出 utility

`extraction/dpc_extractor.py` は library API と別の補助 script です。元 DPC ディレクトリと [Patient List CSV](../specifications/patient-list.md) を受け取り、対象月・識別子を照合します。対象 prefix は `EFn`、`FF1`、`EFg`。患者別の対象期間に合う行を `outputs/<research_id>/<YYMM>/<source file>` に出力し、元の data identifier を research ID に置換します。`summary.csv` に出力ファイル数を記録します。

```bash
python extraction/dpc_extractor.py --path-to-dir <DPC元フォルダ> --target-sheet pt_list.csv --output-root outputs
```

既定の DPC 入力文字コードは cp932、区切り文字はタブ、対象期間の前後 margin は 90 日です。別の形式では引数を明示してください。患者リストの重複、無効な識別子・日付、安全でない research ID は抽出前に拒否されます。入力・出力には機微な情報が含まれるため、施設内の適切な場所で実行し、公開 repository に置かないでください。

PowerShell 高速版は同じ目的の別実装です。配布前に Python 版と合成 fixture の出力一致を確認します。core package の CLI ではありません。
