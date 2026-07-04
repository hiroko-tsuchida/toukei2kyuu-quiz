# 統計検定2級 クイズアプリ 📊

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://toukei2kyuu-quiz.streamlit.app)
[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.58-FF4B4B.svg)](https://streamlit.io/)

統計検定2級（大学教養課程レベルの統計学の知識と問題解決力を問う試験。統計の実務活用・基礎知識の証明・大学院入試などに活用される）の出題範囲を、選択式クイズでその場で解説を見ながら学べる Streamlit アプリです。

🔗 **デモ: https://toukei2kyuu-quiz.streamlit.app** （Streamlit Cloud でデプロイ後に有効になります）

## 特長

- **5問ずつのセットで出題** … 🟢易／🟡標準／🔴難／🟣実践 ごとに5問ずつのセットに分かれ、サイドバーのボタンから選べる
- **選択式でその場採点** … 答えを選ぶと正誤と解説がすぐ表示される
- **解説はやさしい日本語** … 公式だけでなく「なぜそうなるか」を添えて説明
- **スコア集計** … 最後に正解率と判定を表示

全115問（🟢易25＝5セット・🟡標準50＝10セット・🔴難15＝3セット・🟣実践25＝5セット）／10分野（1変数データ／2変数データ／時系列データ／データ収集／確率／確率分布／標本分布／推定／仮説検定／回帰・分散分析）。

分野は[統計検定2級の公式出題範囲表（2018/12/14版）](https://www.toukei-kentei.jp/hubfs/files/grade_range/grade2_hani_20181214.pdf)に基づいて構成しています。

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
