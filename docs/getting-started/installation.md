# 導入

Python 3.12 以降を用意し、公開後は次の方法で導入します。

```bash
python -m pip install open-dpc-jp
```

公開前の候補を試す場合は、配布された wheel のハッシュと入手元を確認し、隔離した環境へ導入してください。DPC 元データや公式マスタは package に同梱しません。

```python
import open_dpc_jp
print(open_dpc_jp.__version__)
```

実際の読込例は [Python の使い方](../usage/python.md)を参照してください。CaseCurator アプリケーションの保存・REDCap export はこの package の機能ではありません。
