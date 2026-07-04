# 統計検定2級 クイズアプリ 📊

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://toukei2kyuu-quiz.streamlit.app)
[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.58-FF4B4B.svg)](https://streamlit.io/)

統計検定2級の主要範囲を、選択式クイズでその場で解説を見ながら学べる Streamlit アプリです。

🔗 **デモ: https://toukei2kyuu-quiz.streamlit.app** （Streamlit Cloud でデプロイ後に有効になります）

## 特長

- **5問ずつのセットで出題** … 🟢易／🟡標準／🔴難／🟣実践 ごとに5問ずつのセットに分かれ、サイドバーのボタンから選べる
- **選択式でその場採点** … 答えを選ぶと正誤と解説がすぐ表示される
- **計算機マーク** … 計算が必要な問題には「🧮 計算機必要！」を表示
- **解説はやさしい日本語** … 公式だけでなく「なぜそうなるか」を添えて説明
- **スコア集計** … 最後に正解率と判定を表示

全75問（🟢易15＝3セット・🟡標準40＝8セット・🔴難10＝2セット・🟣実践10＝2セット）／8分野（記述統計・確率・確率分布・標本分布・推定・仮説検定・カイ二乗・2群比較・相関・回帰）。

> **問題について**：本アプリの問題・選択肢・解説はすべて、統計検定2級の公式出題範囲に沿って独自に作成したオリジナル問題です。実際の公式過去問を転載・引用したものではありません。

## ローカルでの起動

```bash
pip install -r requirements.txt
streamlit run app.py
```

## ファイル構成

| ファイル | 役割 |
|---|---|
| `app.py` | アプリ本体（Streamlit） |
| `questions.py` | 問題データ（選択式・解説つき） |
| `問題.md` / `解答・解説.md` | 読み物版の問題集 |
| `requirements.txt` | 依存パッケージ |

## デプロイ

[Streamlit Community Cloud](https://streamlit.io/cloud) でこのリポジトリを指定し、メインファイルを `app.py` にするだけで公開できます。
