# Charlson Comorbidity Index

標準 `quan-2005@1` はQuan 2005の17条件・原重み・重症側の抑制関係を保持した固定定義です。年齢点は加えません。既定APIも標準Quanのままです。

## MIRAI-ID v1の2026-10-13改訂

公開package **0.1.1**では、研究開始前の調整として `mirai-id-cci@1` 自体を更新しました。
B23/C86/D45の既存拡張に、日本の現行ICD-10と3桁カテゴリー入力への対応を加えています。
標準Quan原表の変更ではありません。

| 入力コード | 改訂前v1の点数 | 改訂後v1の点数 | 変更理由 |
|---|---:|---:|---|
| E10 / E11 / E12 / E13 / E14 | 0 | 1 | 糖尿病は同定できる。合併症不明として最低点 |
| K70 | 0 | 1 | 肝疾患は同定できる。重症度不明として最低点 |
| I85 | 0 | 3 | 全細分類が重症肝疾患条件に該当 |
| Z49 | 0 | 2 | 全細分類が腎疾患条件に該当。血液透析とは断定しない |
| I74 / I74.5など全細分類 | 0 | 1 | 動脈塞栓・血栓症をMIRAI独自に追加 |
| I98.3 | 0 | 3 | 現行日本分類の出血を伴う食道静脈瘤 |
| E119 / E117 / K704 | 1 / 2 / 3 | 1 / 2 / 3 | 細分類の判定を維持 |
| I73（3桁） | 0 | 0 | 対象外の細分類も含む。関連根拠を返し、陽性とは断定しない |

各行はコードを単独で与えた**合成入力のpackage点数**です。CuratorのREDCap選択値と点数は別です。
0は供給されたコードのスコアで、臨床的な疾患不存在を意味しません。

3桁の追加は完全一致です。E11をE119へ補完せず、E117等の細分類は既存判定を維持します。
E10–E14/K70の最低点は「合併症なし」「軽症」の確定ではありません。
重症側の細分類も入力されればそちらを優先します。
評価evidenceの `match_type=exact_category` と `severity_status=unspecified`、
`scoring_basis=minimum_weight` でこの意味を確認できます。

## 分類不足と非検出の区別

[43カテゴリーのスクリーニング](cci-category-screening.md)では、8カテゴリーを陽性に追加し、
35カテゴリーを細分類不足として扱います。後者は `category_evidence` に関連conditionを返し、
`insufficient_category_specificity` を警告します。具体的な対象外細分類にはこの扱いを適用しません。

Curatorは既存の時期・診断role・疑い設定を適用します。関連カテゴリーが有効な既往根拠にある場合、
参考根拠として原資料確認を促し、その項目のDPC非検出推定Noを抑止します。
共通packageは時期・疑い・臨床的確定を判断しません。

## I74を含める理由と範囲

CCIの臨床的運用には急性動脈不全を含める例があります。
日本分類のI74は動脈塞栓症・血栓症で、冠・脳・肺・腸間膜・腎・網膜の塞栓症は別分類へ除外されています。
大動脈・四肢・腸骨・その他／部位不明を含むI74全体を、MIRAIの末梢血管疾患へ追加します。
静脈血栓症や肺塞栓症をこの拡張で加点しません。
これはQuanとの差分を明示した研究上の選択であり、予測性能の検証結果ではありません。

出典：[厚労省の循環器分類](https://www.mhlw.go.jp/toukei/sippei/dl/naiyou09.pdf)、
[臨床試験プロトコルのCCI規則（Appendix H）](https://cdn.clinicaltrials.gov/large-docs/00/NCT00553800/Prot_SAP_000.pdf)。

## 版・由来と旧結果の再現

同じ `mirai-id-cci@1` でも改訂前後でsource hashが異なります。
論文・解析ではpackage版、定義名・版・SHA-256、algorithm版、schemaを記録してください。
改訂版はalgorithm 2、標準Quanと改訂前の保存JSONはalgorithm 1です。
元の入力コードを保ち、Curatorの採用済み値は候補更新だけで書き換えません。

改訂前JSONもwheelに同梱します。旧結果はそのPathを `definition` に指定して再現できます。
詳細なhash、再現コード、B23/C86/D45を含む由来は公開repositoryの
[MIRAI-ID-CCI-PROVENANCE.md](https://github.com/sy-wada/open-dpc-jp/blob/main/MIRAI-ID-CCI-PROVENANCE.md)を参照してください。

原著：[Quan H, et al. 2005](https://pubmed.ncbi.nlm.nih.gov/16224307/).
*Medical Care*. 43:1130–1139. DOI: `10.1097/01.mlr.0000182534.19832.83`。
