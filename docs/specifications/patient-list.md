# Patient List CSV 仕様

この仕様は DPC 抽出 utility と [患者リスト作成ツール](../tools/patient-list-generator-guide.md)の共通契約です。CSV は UTF-8 BOM 付き、カンマ区切りで、次の header 順序を使用します。

```text
pt_id,research_id,data_identifier,event_date,encounter_start_date,encounter_end_date
```

| 列 | 必須 | 内容 |
|---|---|---|
| `pt_id` | いいえ | 元研究等の識別子。空欄可 |
| `research_id` | はい | 抽出後のディレクトリ名・置換 ID。英数字で始まり、英数字・`_`・`-` のみ。Windows 予約名と重複は不可 |
| `data_identifier` | はい | DPC 元データと照合する 10 桁の半角数字。重複不可 |
| `event_date` | いいえ | 基準イベント日。空欄可 |
| `encounter_start_date` | はい | 抽出対象期間の開始日 |
| `encounter_end_date` | はい | 抽出対象期間の終了日 |

日付は実在する暦日を `YYYYMMDD` で記載します。開始日は終了日以前でなければなりません。Web ツールは `YYYY-MM-DD` と `YYYY/MM/DD` を警告付きで正規化できますが、`04/05/2026` のような曖昧な日付は受け付けません。`event_date` が対象期間外の場合は警告です。

抽出 utility は旧形式の 1–9 桁の半角数字を 10 桁へゼロ埋めして読み込めます。公開用 CSV は常に 10 桁で出力します。識別子を表計算ソフトの数値型に変換すると先頭ゼロが失われるため、文字列として扱ってください。

どの項目にも改行を含められません。患者リストと抽出結果は識別可能な情報を含み得ます。公開 issue やサンプルに実データを添付しないでください。
