# DPC 入力と年度

core は FF1、EFn、EFg の構造的読込を提供します。既定の文字コードは cp932 です。読込結果は source hash、raw cells、未知 code、余剰列、診断を保持し、欠落や不正を診断情報として返します。完全な DPC 提出妥当性や臨床適格性は判定しません。

収録した schema profile は 2014–2026 年の年度・改訂別です。2024 年と 2026 年には有効日で分かれる profile があり、年だけでは一意に選べない場合があります。schema ID を固定すると将来の release でも再現しやすくなります。各 profile の出典と検証範囲は package の `spec/dpc/source_ledger.json` と `spec/dpc/registry.json` を参照してください。

古い混合年度動作は `legacy-mixed-v1` として保持します。これは公式の単一年度仕様を表すものではありません。未対応年度で fallback を明示した場合、結果に警告が付きます。臨床的な互換性は自動で保証されません。
