# Charlson Comorbidity Index

Open DPC JP は定義と計算アルゴリズムを分けて版管理します。`quan-2005` は Quan et al. 2005 の ICD-10 コード群を基にした 17 条件の定義です。年齢点は加えません。重症条件が同群の軽症条件を抑制する場合も、判断根拠を返します。

`mirai-id-cci@1` は別の研究定義です。`quan-2005` に対して B23、C86、D45 の扱いを追加した版であり、同じ名称のまま Quan 定義へ上書きしていません。詳細な根拠と変更範囲は package の `MIRAI-ID-CCI-PROVENANCE.md` に記載しています。

どちらも入力として与えたコード集合に対する計算です。入力の完全性、原資料との一致、診断確定、研究対象集団の選択は呼出側が判断します。欠損を「疾患なし」に変換しません。論文・解析では定義名、版、source hash、schema と package 版を記録してください。

原著: Quan H, et al. Coding algorithms for defining comorbidities in ICD-9-CM and ICD-10 administrative data. *Medical Care*. 2005;43:1130–1139. DOI: `10.1097/01.mlr.0000182534.19832.83`。
