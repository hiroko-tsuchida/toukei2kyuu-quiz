"""統計検定2級 クイズアプリ（Streamlit）

使い方:
    streamlit run app.py
"""

import random

import streamlit as st

from questions import QUESTIONS

st.set_page_config(page_title="統計検定2級 クイズ", page_icon="📊", layout="centered")


# ------------------------------------------------------------------
# セッション状態の初期化
# ------------------------------------------------------------------
def init_state():
    """出題する問題リストや回答状況をセッションに用意する。"""
    if "order" not in st.session_state:
        start_quiz(QUESTIONS)


def start_quiz(question_pool, shuffle=False):
    """選んだ問題で新しいクイズを始める。"""
    pool = list(question_pool)
    if shuffle:
        random.shuffle(pool)
    st.session_state.order = pool
    st.session_state.index = 0          # 今が何問目か
    st.session_state.score = 0          # 正解数
    st.session_state.answered = False   # 現在の問題に回答済みか
    st.session_state.selected = None    # 選んだ選択肢
    st.session_state.finished = False   # 全問終わったか


# ------------------------------------------------------------------
# サイドバー（分野の絞り込み・出題設定）
# ------------------------------------------------------------------
def sidebar_controls():
    st.sidebar.header("⚙️ 出題設定")

    categories = ["すべて"] + sorted({q["category"] for q in QUESTIONS})
    chosen = st.sidebar.selectbox("分野を選ぶ", categories)

    # 難易度は決まった順番で並べる（基礎→標準→応用）
    level_order = ["基礎", "標準", "応用"]
    present = [lv for lv in level_order if any(q["level"] == lv for q in QUESTIONS)]
    levels = ["すべて"] + present
    chosen_level = st.sidebar.selectbox("難易度を選ぶ", levels)

    shuffle = st.sidebar.checkbox("問題の順番をシャッフル", value=False)

    pool = QUESTIONS
    if chosen != "すべて":
        pool = [q for q in pool if q["category"] == chosen]
    if chosen_level != "すべて":
        pool = [q for q in pool if q["level"] == chosen_level]

    st.sidebar.caption(f"この条件の問題数: {len(pool)} 問")

    if st.sidebar.button(
        "この設定でスタート / リセット",
        use_container_width=True,
        disabled=len(pool) == 0,
    ):
        start_quiz(pool, shuffle=shuffle)
        st.rerun()

    if len(pool) == 0:
        st.sidebar.warning("この条件に合う問題がありません。条件を変えてください。")

    st.sidebar.markdown("---")
    st.sidebar.caption(f"全{len(QUESTIONS)}問から出題できます。")


# ------------------------------------------------------------------
# 結果画面
# ------------------------------------------------------------------
def show_result():
    total = len(st.session_state.order)
    score = st.session_state.score
    rate = score / total * 100 if total else 0

    st.subheader("🎉 おつかれさまでした！")
    st.metric("スコア", f"{score} / {total}", f"{rate:.0f}%")

    if rate >= 80:
        st.success("すばらしい！合格圏内のレベルです。")
    elif rate >= 60:
        st.info("あと少し！まちがえた分野を復習しましょう。")
    else:
        st.warning("基礎をもう一度確認すると伸びます。あせらず復習しましょう。")

    if st.button("もう一度挑戦する", use_container_width=True):
        start_quiz(st.session_state.order)
        st.rerun()


# ------------------------------------------------------------------
# 問題画面
# ------------------------------------------------------------------
def show_question():
    order = st.session_state.order
    i = st.session_state.index
    q = order[i]
    total = len(order)

    # 進捗バー
    st.progress((i) / total, text=f"第 {i + 1} 問 / 全 {total} 問")
    badge = {"基礎": "🟢", "標準": "🟡", "応用": "🔴"}.get(q["level"], "")
    st.caption(f"分野: {q['category']} ｜ 難易度: {badge} {q['level']}")
    st.markdown(f"### Q{i + 1}. {q['question']}")
    if q.get("calc"):
        st.warning("🧮 電卓必要！")

    # 回答前：選択肢を表示
    if not st.session_state.answered:
        selected = st.radio(
            "答えを選んでください",
            options=list(range(len(q["choices"]))),
            format_func=lambda x: q["choices"][x],
            index=None,
            key=f"radio_{q['id']}",
        )
        if st.button("回答する", use_container_width=True, disabled=selected is None):
            st.session_state.selected = selected
            st.session_state.answered = True
            if selected == q["answer"]:
                st.session_state.score += 1
            st.rerun()

    # 回答後：正誤と解説を表示
    else:
        selected = st.session_state.selected
        for idx, choice in enumerate(q["choices"]):
            if idx == q["answer"]:
                st.markdown(f"- ✅ **{choice}**（正解）")
            elif idx == selected:
                st.markdown(f"- ❌ ~~{choice}~~（あなたの回答）")
            else:
                st.markdown(f"- {choice}")

        if selected == q["answer"]:
            st.success("正解！")
        else:
            st.error("不正解…")

        st.info(f"💡 解説: {q['explanation']}")

        label = "次の問題へ" if i + 1 < total else "結果を見る"
        if st.button(label, use_container_width=True):
            st.session_state.answered = False
            st.session_state.selected = None
            if i + 1 < total:
                st.session_state.index += 1
            else:
                st.session_state.finished = True
            st.rerun()

    # 現在のスコアをそっと表示
    st.caption(f"現在のスコア: {st.session_state.score} 問正解")


# ------------------------------------------------------------------
# メイン
# ------------------------------------------------------------------
def main():
    st.title("📊 統計検定2級 クイズ")
    st.caption("選択式の問題に答えて、その場で解説を確認できます。")

    init_state()
    sidebar_controls()

    if st.session_state.finished:
        show_result()
    else:
        show_question()


if __name__ == "__main__":
    main()
