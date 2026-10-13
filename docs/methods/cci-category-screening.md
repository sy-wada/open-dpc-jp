# 日本ICD-10のCCIカテゴリー入力スクリーニング（2026-10-13）

対象は改訂前MIRAI-ID v1の4桁prefixに対応する、既存3桁prefixで覆われていない43個の親カテゴリー。
厚労省のICD-10（2013年版）準拠・現行内容例示表11章を照合した。病名マスター20260601との補助照合ではE10–E14の3桁入力が実在する。
ここでいう「非該当細分類」は現行MIRAIのコード集合への非該当であり、臨床的な疾患不存在を意味しない。
共通細分類を使用するE10–E14とN03/N05は共通表の0–9を展開した。分類資料の取得hashは末尾に記録する。

8カテゴリーを完全一致で陽性に追加する。残る35カテゴリーは細分類不足として関連conditionを返す。
追加の細分類I983と、新しい系列I74は下の43カテゴリー集計とは区別する。

| 親 | 日本分類の細分類（小数点省略） | 現行MIRAIで非該当の細分類 | 採否・理由 | 出典 |
|---|---|---|---|---|
| E10 | E100, E101, E102, E103, E104, E105, E106, E107, E108, E109 | なし（重症度の異なる細分類を含み得る） | 採用：疾患は同定、重症度不明の最低1点 | [内容例示表 p.6](https://www.mhlw.go.jp/toukei/sippei/dl/naiyou04.pdf) |
| E11 | E110, E111, E112, E113, E114, E115, E116, E117, E118, E119 | なし（重症度の異なる細分類を含み得る） | 採用：疾患は同定、重症度不明の最低1点 | [内容例示表 p.6](https://www.mhlw.go.jp/toukei/sippei/dl/naiyou04.pdf) |
| E12 | E120, E121, E122, E123, E124, E125, E126, E127, E128, E129 | なし（重症度の異なる細分類を含み得る） | 採用：疾患は同定、重症度不明の最低1点 | [内容例示表 p.6](https://www.mhlw.go.jp/toukei/sippei/dl/naiyou04.pdf) |
| E13 | E130, E131, E132, E133, E134, E135, E136, E137, E138, E139 | なし（重症度の異なる細分類を含み得る） | 採用：疾患は同定、重症度不明の最低1点 | [内容例示表 p.6](https://www.mhlw.go.jp/toukei/sippei/dl/naiyou04.pdf) |
| E14 | E140, E141, E142, E143, E144, E145, E146, E147, E148, E149 | なし（重症度の異なる細分類を含み得る） | 採用：疾患は同定、重症度不明の最低1点 | [内容例示表 p.6](https://www.mhlw.go.jp/toukei/sippei/dl/naiyou04.pdf) |
| F05 | F050, F051, F058, F059 | F050, F058, F059 | 陽性へ拡張しない：対象外細分類を含む。カテゴリーのみなら参考・推定No抑止 | [内容例示表 p.6](https://www.mhlw.go.jp/toukei/sippei/dl/naiyou05.pdf) |
| G04 | G040, G041, G042, G048, G049 | G040, G042, G048, G049 | 陽性へ拡張しない：対象外細分類を含む。カテゴリーのみなら参考・推定No抑止 | [内容例示表 p.5](https://www.mhlw.go.jp/toukei/sippei/dl/naiyou06.pdf) |
| G11 | G110, G111, G112, G113, G114, G118, G119 | G110, G111, G112, G113, G118, G119 | 陽性へ拡張しない：対象外細分類を含む。カテゴリーのみなら参考・推定No抑止 | [内容例示表 p.8](https://www.mhlw.go.jp/toukei/sippei/dl/naiyou06.pdf) |
| G31 | G310, G311, G312, G318, G319 | G310, G312, G318, G319 | 陽性へ拡張しない：対象外細分類を含む。カテゴリーのみなら参考・推定No抑止 | [内容例示表 p.14](https://www.mhlw.go.jp/toukei/sippei/dl/naiyou06.pdf) |
| G80 | G800, G801, G802, G803, G804, G808, G809 | G800, G803, G804, G808, G809 | 陽性へ拡張しない：対象外細分類を含む。カテゴリーのみなら参考・推定No抑止 | [内容例示表 p.32](https://www.mhlw.go.jp/toukei/sippei/dl/naiyou06.pdf) |
| G83 | G830, G831, G832, G833, G834, G838, G839 | G838 | 陽性へ拡張しない：対象外細分類を含む。カテゴリーのみなら参考・推定No抑止 | [内容例示表 p.33](https://www.mhlw.go.jp/toukei/sippei/dl/naiyou06.pdf) |
| H34 | H340, H341, H342, H348, H349 | H341, H342, H348, H349 | 陽性へ拡張しない：対象外細分類を含む。カテゴリーのみなら参考・推定No抑止 | [内容例示表 p.18](https://www.mhlw.go.jp/toukei/sippei/dl/naiyou07.pdf) |
| I09 | I090, I091, I092, I098, I099 | I090, I091, I092, I098 | 陽性へ拡張しない：対象外細分類を含む。カテゴリーのみなら参考・推定No抑止 | [内容例示表 p.5](https://www.mhlw.go.jp/toukei/sippei/dl/naiyou09.pdf) |
| I11 | I110, I119 | I119 | 陽性へ拡張しない：対象外細分類を含む。カテゴリーのみなら参考・推定No抑止 | [内容例示表 p.6](https://www.mhlw.go.jp/toukei/sippei/dl/naiyou09.pdf) |
| I12 | I120, I129 | I129 | 陽性へ拡張しない：対象外細分類を含む。カテゴリーのみなら参考・推定No抑止 | [内容例示表 p.6](https://www.mhlw.go.jp/toukei/sippei/dl/naiyou09.pdf) |
| I13 | I130, I131, I132, I139 | I139 | 陽性へ拡張しない：対象外細分類を含む。カテゴリーのみなら参考・推定No抑止 | [内容例示表 p.7](https://www.mhlw.go.jp/toukei/sippei/dl/naiyou09.pdf) |
| I25 | I250, I251, I252, I253, I254, I255, I256, I258, I259 | I250, I251, I253, I254, I256, I258, I259 | 陽性へ拡張しない：対象外細分類を含む。カテゴリーのみなら参考・推定No抑止 | [内容例示表 p.11](https://www.mhlw.go.jp/toukei/sippei/dl/naiyou09.pdf) |
| I27 | I270, I271, I272, I278, I279 | I270, I271, I272 | 陽性へ拡張しない：対象外細分類を含む。カテゴリーのみなら参考・推定No抑止 | [内容例示表 p.13](https://www.mhlw.go.jp/toukei/sippei/dl/naiyou09.pdf) |
| I42 | I420, I421, I422, I423, I424, I425, I426, I427, I428, I429 | I421, I422, I423, I424 | 陽性へ拡張しない：対象外細分類を含む。カテゴリーのみなら参考・推定No抑止 | [内容例示表 p.19](https://www.mhlw.go.jp/toukei/sippei/dl/naiyou09.pdf) |
| I73 | I730, I731, I738, I739 | I730 | 陽性へ拡張しない：対象外細分類を含む。カテゴリーのみなら参考・推定No抑止 | [内容例示表 p.33](https://www.mhlw.go.jp/toukei/sippei/dl/naiyou09.pdf) |
| I77 | I770, I771, I772, I773, I774, I775, I776, I778, I779 | I770, I772, I773, I774, I775, I776, I778, I779 | 陽性へ拡張しない：対象外細分類を含む。カテゴリーのみなら参考・推定No抑止 | [内容例示表 p.35](https://www.mhlw.go.jp/toukei/sippei/dl/naiyou09.pdf) |
| I79 | I790, I791, I792, I798 | I791, I798 | 陽性へ拡張しない：対象外細分類を含む。カテゴリーのみなら参考・推定No抑止 | [内容例示表 p.36](https://www.mhlw.go.jp/toukei/sippei/dl/naiyou09.pdf) |
| I85 | I850, I859 | なし（重症度の異なる細分類を含み得る） | 採用：全細分類が重症肝疾患（3点） | [内容例示表 p.39](https://www.mhlw.go.jp/toukei/sippei/dl/naiyou09.pdf) |
| I86 | I860, I861, I862, I863, I864, I868 | I860, I861, I862, I863, I868 | 陽性へ拡張しない：対象外細分類を含む。カテゴリーのみなら参考・推定No抑止 | [内容例示表 p.39](https://www.mhlw.go.jp/toukei/sippei/dl/naiyou09.pdf) |
| I98 | I980, I981, I982, I983, I988 | I980, I981, I988 | 陽性へ拡張しない：対象外細分類を含む。カテゴリーのみなら参考・推定No抑止 | [内容例示表 p.42](https://www.mhlw.go.jp/toukei/sippei/dl/naiyou09.pdf) |
| J68 | J680, J681, J682, J683, J684, J688, J689 | J680, J681, J682, J683, J688, J689 | 陽性へ拡張しない：対象外細分類を含む。カテゴリーのみなら参考・推定No抑止 | [内容例示表 p.26](https://www.mhlw.go.jp/toukei/sippei/dl/naiyou10.pdf) |
| J70 | J700, J701, J702, J703, J704, J708, J709 | J700, J702, J704, J708, J709 | 陽性へ拡張しない：対象外細分類を含む。カテゴリーのみなら参考・推定No抑止 | [内容例示表 p.27](https://www.mhlw.go.jp/toukei/sippei/dl/naiyou10.pdf) |
| K55 | K550, K551, K552, K558, K559 | K550, K552 | 陽性へ拡張しない：対象外細分類を含む。カテゴリーのみなら参考・推定No抑止 | [内容例示表 p.30](https://www.mhlw.go.jp/toukei/sippei/dl/naiyou11.pdf) |
| K70 | K700, K701, K702, K703, K704, K709 | なし（重症度の異なる細分類を含み得る） | 採用：疾患は同定、重症度不明の最低1点 | [内容例示表 p.40](https://www.mhlw.go.jp/toukei/sippei/dl/naiyou11.pdf) |
| K71 | K710, K711, K712, K713, K714, K715, K716, K717, K718, K719 | K710, K712, K716, K718, K719 | 陽性へ拡張しない：対象外細分類を含む。カテゴリーのみなら参考・推定No抑止 | [内容例示表 p.40](https://www.mhlw.go.jp/toukei/sippei/dl/naiyou11.pdf) |
| K72 | K720, K721, K729 | K720 | 陽性へ拡張しない：対象外細分類を含む。カテゴリーのみなら参考・推定No抑止 | [内容例示表 p.41](https://www.mhlw.go.jp/toukei/sippei/dl/naiyou11.pdf) |
| K76 | K760, K761, K762, K763, K764, K765, K766, K767, K768, K769 | K761 | 陽性へ拡張しない：対象外細分類を含む。カテゴリーのみなら参考・推定No抑止 | [内容例示表 p.44](https://www.mhlw.go.jp/toukei/sippei/dl/naiyou11.pdf) |
| M31 | M310, M311, M312, M313, M314, M315, M316, M317, M318, M319 | M310, M311, M312, M313, M314, M316, M317, M318, M319 | 陽性へ拡張しない：対象外細分類を含む。カテゴリーのみなら参考・推定No抑止 | [内容例示表 p.20](https://www.mhlw.go.jp/toukei/sippei/dl/naiyou13.pdf) |
| M35 | M350, M351, M352, M353, M354, M355, M356, M357, M358, M359 | M350, M352, M354, M355, M356, M357, M358, M359 | 陽性へ拡張しない：対象外細分類を含む。カテゴリーのみなら参考・推定No抑止 | [内容例示表 p.22](https://www.mhlw.go.jp/toukei/sippei/dl/naiyou13.pdf) |
| M36 | M360, M361, M362, M363, M364, M368 | M361, M362, M363, M364, M368 | 陽性へ拡張しない：対象外細分類を含む。カテゴリーのみなら参考・推定No抑止 | [内容例示表 p.23](https://www.mhlw.go.jp/toukei/sippei/dl/naiyou13.pdf) |
| N03 | N030, N031, N032, N033, N034, N035, N036, N037, N038, N039 | N030, N031, N038, N039 | 陽性へ拡張しない：対象外細分類を含む。カテゴリーのみなら参考・推定No抑止 | [内容例示表 p.2](https://www.mhlw.go.jp/toukei/sippei/dl/naiyou14.pdf) |
| N05 | N050, N051, N052, N053, N054, N055, N056, N057, N058, N059 | N050, N051, N058, N059 | 陽性へ拡張しない：対象外細分類を含む。カテゴリーのみなら参考・推定No抑止 | [内容例示表 p.2](https://www.mhlw.go.jp/toukei/sippei/dl/naiyou14.pdf) |
| N25 | N250, N251, N258, N259 | N251, N258, N259 | 陽性へ拡張しない：対象外細分類を含む。カテゴリーのみなら参考・推定No抑止 | [内容例示表 p.14](https://www.mhlw.go.jp/toukei/sippei/dl/naiyou14.pdf) |
| P29 | P290, P291, P292, P293, P294, P298, P299 | P291, P292, P293, P294, P298, P299 | 陽性へ拡張しない：対象外細分類を含む。カテゴリーのみなら参考・推定No抑止 | [内容例示表 p.15](https://www.mhlw.go.jp/toukei/sippei/dl/naiyou16.pdf) |
| Z49 | Z490, Z491, Z492 | なし（重症度の異なる細分類を含み得る） | 採用：全細分類が腎疾患（2点）。透析種別は不明 | [内容例示表 p.20](https://www.mhlw.go.jp/toukei/sippei/dl/naiyou21.pdf) |
| Z94 | Z940, Z941, Z942, Z943, Z944, Z945, Z946, Z947, Z948, Z949 | Z941, Z942, Z943, Z945, Z946, Z947, Z948, Z949 | 陽性へ拡張しない：対象外細分類を含む。カテゴリーのみなら参考・推定No抑止 | [内容例示表 p.44](https://www.mhlw.go.jp/toukei/sippei/dl/naiyou21.pdf) |
| Z95 | Z950, Z951, Z952, Z953, Z954, Z955, Z958, Z959 | Z950, Z951, Z952, Z953, Z954, Z955 | 陽性へ拡張しない：対象外細分類を含む。カテゴリーのみなら参考・推定No抑止 | [内容例示表 p.44](https://www.mhlw.go.jp/toukei/sippei/dl/naiyou21.pdf) |
| Z99 | Z990, Z991, Z992, Z993, Z994, Z998, Z999 | Z990, Z991, Z993, Z994, Z998, Z999 | 陽性へ拡張しない：対象外細分類を含む。カテゴリーのみなら参考・推定No抑止 | [内容例示表 p.46](https://www.mhlw.go.jp/toukei/sippei/dl/naiyou21.pdf) |

## 集計外の追加・候補

- I74 / I740–I745 / I748 / I749：動脈塞栓症・血栓症を末梢血管疾患へ追加。急性動脈不全を含む臨床的CCI運用を根拠とするMIRAI独自拡張で、Quan原表への追加ではない。
- I983：日本分類の「他に分類される疾患における出血を伴う食道静脈瘤」を重症肝疾患へ追加。
- I72等の現行Quan外の系列、M350/M314等のその他細分類は今回追加しない。カテゴリーを読み替えて個別の非該当細分類まで拡張しない。
- E11をE119へ、K70をK709へ補完しない。糖尿病・肝疾患の最低点は重症度の確認結果ではない。

## 照合資料のsource-byte SHA-256

取得日2026-10-13。[厚労省分類一覧](https://www.mhlw.go.jp/toukei/sippei/index.html)。PDF自体と病名マスターは公開packageへコピーしない。

- 第4章 naiyou04（naiyou04.pdf）：`25aca62f75566d4b309dcfa534b95965df34122155638e594f713bb2c3e7fe81`
- 第5章 naiyou05（naiyou05.pdf）：`fdc67d3c84f68d7510665a58b0066943eb5fee1d30435e0a9d6725fc94a9e94c`
- 第6章 naiyou06（naiyou06.pdf）：`50755b251877fd0bff4588da35a450451f98e14cb5bac5ebfc09bff33572c68f`
- 第7章 naiyou07（naiyou07.pdf）：`e461cd0b9d60e562fc5babc71db9a53634239ed611a1cb6d37a0ce34a72eb114`
- 第9章 naiyou09（naiyou09.pdf）：`14bb21cecaab5a7fd5d04426fbf6a192c8783c3b72b3b0c6ca49cf52f65f9913`
- 第10章 naiyou10（naiyou10.pdf）：`c6ba23cef8a55260ae8208b333bbae4f6e7d73121fc17b67bd965e11fcff7b2a`
- 第11章 naiyou11（naiyou11.pdf）：`4ffddb83aa9d44809b2fa1a2ff43c3860448c840053f12fd5980cd58fcd06108`
- 第13章 naiyou13（naiyou13.pdf）：`2effb56a99f7839b194e9eda8165492d8aef49a6cb06014ab5086b0b466e86c3`
- 第14章 naiyou14（naiyou14.pdf）：`9df0d77746f435a5122e242cb383eef81addd4299a63897a89971b52d13674a7`
- 第16章 naiyou16（naiyou16.pdf）：`05ea9791e958c07f5f386d47390cd9601488c25515482499148a53be7bb75ae7`
- 第21章 naiyou21（naiyou21.pdf）：`069b657d7efebd5d3b71656e1d2345d9c348693e19ab14dc95d155d10f79a7ce`
