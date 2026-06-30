"""統計検定2級 クイズアプリ（Streamlit）

使い方:
    streamlit run app.py
"""

import random

import streamlit as st

from questions import QUESTIONS

st.set_page_config(page_title="統計検定2級 クイズ", page_icon="📊", layout="centered")

MAX_QUESTIONS = 5  # 1回の出題は最大この問題数まで
LEVELS = ["易", "標準", "難"]  # 難易度の表示順
LEVEL_BADGE = {"易": "🟢", "標準": "🟡", "難": "🔴"}


def pick_questions(pool):
    """プールから最大 MAX_QUESTIONS 問をランダムに選ぶ。"""
    pool = list(pool)
    if len(pool) > MAX_QUESTIONS:
        return random.sample(pool, MAX_QUESTIONS)
    random.shuffle(pool)
    return pool


# ------------------------------------------------------------------
# セッション状態の初期化
# ------------------------------------------------------------------
def init_state():
    """セッション状態を初期化する。最初は未開始（難易度を選ぶまで待つ）。"""
    if "order" not in st.session_state:
        st.session_state.order = None  # まだ難易度が選ばれていない


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
    st.sidebar.header("⚙️ 難易度を選ぶ")
    st.sidebar.caption(f"選ぶとすぐに始まります（最大{MAX_QUESTIONS}問）👇")

    # 易・標準・難 のボタンを縦一列に並べる
    for level in LEVELS:
        pool = [q for q in QUESTIONS if q["level"] == level]
        badge = LEVEL_BADGE[level]
        if st.sidebar.button(
            f"{badge} {level}（{len(pool)}問）",
            use_container_width=True,
            key=f"level_{level}",
            disabled=len(pool) == 0,
        ):
            start_quiz(pick_questions(pool))
            st.rerun()

    st.sidebar.markdown("---")
    counts = " ／ ".join(
        f"{LEVEL_BADGE[lv]}{lv} {sum(1 for q in QUESTIONS if q['level'] == lv)}問"
        for lv in LEVELS
    )
    st.sidebar.caption(f"全{len(QUESTIONS)}問　{counts}")


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
        st.warning("やさしい問題（易）から見直すと伸びます。あせらず復習しましょう。")

    st.caption("← サイドバーの難易度ボタンから次の問題に挑戦できます。")


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
    badge = LEVEL_BADGE.get(q["level"], "")
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

    if st.session_state.order is None:
        st.info("👈 左のサイドバーから難易度（易・標準・難）を選ぶと、クイズが始まります。")
        st.markdown(
            f"- 各難易度から**最大{MAX_QUESTIONS}問**がランダムに出題されます\n"
            "- 答えを選ぶと、その場で正誤と解説が表示されます"
        )
    elif st.session_state.finished:
        show_result()
    else:
        show_question()


if __name__ == "__main__":
    main()
