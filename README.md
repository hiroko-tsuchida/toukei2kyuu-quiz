# 統計検定2級 クイズアプリ 📊

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://toukei2kyuu-quiz.streamlit.app)
[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.58-FF4B4B.svg)](https://streamlit.io/)

統計検定2級の主要範囲を、選択式クイズでその場で解説を見ながら学べる Streamlit アプリです。

🔗 **デモ: https://toukei2kyuu-quiz.streamlit.app** （Streamlit Cloud でデプロイ後に有効になります）

## 特長

- **難易度で選んで出題** … 🟢易／🟡標準／🔴難 をサイドバーから選ぶと、最大5問がランダムに出題される
- **選択式でその場採点** … 答えを選ぶと正誤と解説がすぐ表示される
- **電卓マーク** … 計算が必要な問題には「🧮 電卓必要！」を表示
- **解説はやさしい日本語** … 公式だけでなく「なぜそうなるか」を添えて説明
- **進捗バー＋スコア集計** … 最後に正解率と判定を表示

全56問（🟢易15・🟡標準36・🔴難5）／8分野（記述統計・確率・確率分布・標本分布・推定・仮説検定・カイ二乗・2群比較・相関・回帰）。

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
