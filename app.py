"""統計検定2級 クイズアプリ（Streamlit）

使い方:
    streamlit run app.py
"""

import json
import random

import streamlit as st
from streamlit_local_storage import LocalStorage

from questions import QUESTIONS

st.set_page_config(page_title="統計検定2級 クイズ", page_icon="📊", layout="centered")

SET_SIZE = 5  # 1セットあたりの問題数
LEVELS = ["易", "標準", "難", "実践"]  # 難易度の表示順
LEVEL_BADGE = {"易": "🟢", "標準": "🟡", "難": "🔴", "実践": "🟣"}
STORAGE_KEY = "toukei2kyuu_results"  # 端末（localStorage）に保存するキー


def build_sets(level, size=SET_SIZE):
    """ある難易度の問題を、並び順に size 問ずつのセットに分ける。"""
    qs = [q for q in QUESTIONS if q["level"] == level]
    return [qs[i : i + size] for i in range(0, len(qs), size)]


def all_set_labels():
    """全セットのラベル（例: 易1, 標準3, 難1）を表示順で返す。"""
    labels = []
    for level in LEVELS:
        for i in range(len(build_sets(level))):
            labels.append(f"{level}{i + 1}")
    return labels


def draw_stats():
    """成績ダッシュボード（全制覇のお知らせと案内）を表示する。"""
    results = st.session_state.get("results", {})
    total = len(all_set_labels())

    # 全セット制覇のお知らせ
    if results and len(results) == total:
        st.success("🎉 全12セット制覇！コンプリートおめでとうございます！")

    st.caption("※ セットごとの達成率は、左のサイドバーの各セットの下に表示されます。")


# ------------------------------------------------------------------
# セッション状態の初期化
# ------------------------------------------------------------------
def init_state(local_storage):
    """セッション状態を初期化する。達成率は端末（localStorage）から読み込む。"""
    if "order" not in st.session_state:
        st.session_state.order = None  # まだ難易度が選ばれていない
    if "results" not in st.session_state:
        # 端末に保存された達成率を読み込む（なければ空）
        raw = local_storage.getItem(STORAGE_KEY)
        try:
            st.session_state.results = json.loads(raw) if raw else {}
        except (ValueError, TypeError):
            st.session_state.results = {}


def start_quiz(question_pool, label=None, shuffle=False):
    """選んだ問題で新しいクイズを始める。"""
    pool = list(question_pool)
    if shuffle:
        random.shuffle(pool)
    st.session_state.order = pool
    st.session_state.current_set = label  # いま挑戦中のセット名
    st.session_state.index = 0          # 今が何問目か
    st.session_state.score = 0          # 正解数
    st.session_state.answered = False   # 現在の問題に回答済みか
    st.session_state.selected = None    # 選んだ選択肢
    st.session_state.finished = False   # 全問終わったか
    st.session_state.result_saved = False  # 結果を保存済みか


# ------------------------------------------------------------------
# サイドバー（分野の絞り込み・出題設定）
# ------------------------------------------------------------------
def sidebar_controls(local_storage):
    st.sidebar.header("⚙️ 出題セットを選ぶ")
    st.sidebar.caption(f"ボタンを押すとその{SET_SIZE}問が始まります 👇")

    # 難易度ごとに、5問ずつのセットボタンを縦一列に並べる
    for level in LEVELS:
        sets = build_sets(level)
        if not sets:
            continue
        st.sidebar.markdown(f"**{LEVEL_BADGE[level]} {level}（{sum(len(s) for s in sets)}問）**")
        results = st.session_state.get("results", {})
        for i, s in enumerate(sets):
            label = f"{level}{i + 1}"
            if st.sidebar.button(
                f"セット{i + 1}（{len(s)}問）",
                use_container_width=True,
                key=f"set_{level}_{i}",
            ):
                start_quiz(s, label=label)
                st.rerun()
            # ボタンの下にそのセットの達成率を表示する
            if label in results:
                rate = results[label]
                st.sidebar.progress(rate / 100, text=f"達成率 {rate:.0f}%")
            else:
                st.sidebar.caption("　未挑戦")

    st.sidebar.markdown("---")
    counts = " ／ ".join(
        f"{LEVEL_BADGE[lv]}{lv} {sum(1 for q in QUESTIONS if q['level'] == lv)}問"
        for lv in LEVELS
    )
    st.sidebar.caption(f"全{len(QUESTIONS)}問　{counts}")

    if st.session_state.get("results") and st.sidebar.button(
        "🗑️ 達成率の記録をリセット", use_container_width=True
    ):
        st.session_state.results = {}
        local_storage.setItem(STORAGE_KEY, json.dumps({}))
        st.rerun()


# ------------------------------------------------------------------
# 結果画面
# ------------------------------------------------------------------
def record_result(local_storage):
    """終了したセットの達成率を記録し、端末（localStorage）にも保存する。
    サイドバーを描く前に呼ぶことで、各セットの達成率がすぐ反映される。"""
    if st.session_state.get("result_saved"):
        return
    label = st.session_state.get("current_set")
    total = len(st.session_state.order)
    score = st.session_state.score
    rate = score / total * 100 if total else 0
    if label:
        st.session_state.results[label] = rate
        local_storage.setItem(STORAGE_KEY, json.dumps(st.session_state.results))
    st.session_state.result_saved = True
    # 全セット制覇した瞬間だけ風船を飛ばす
    if len(st.session_state.results) == len(all_set_labels()):
        st.balloons()


def show_result():
    total = len(st.session_state.order)
    score = st.session_state.score
    rate = score / total * 100 if total else 0
    label = st.session_state.get("current_set")

    st.subheader("🎉 おつかれさまでした！")
    set_name = f"（{label}）" if label else ""
    st.metric(f"スコア{set_name}", f"{score} / {total}", f"{rate:.0f}%")

    if rate >= 80:
        st.success("すばらしい！合格圏内のレベルです。")
    elif rate >= 60:
        st.info("あと少し！まちがえた分野を復習しましょう。")
    else:
        st.warning("やさしい問題（易）から見直すと伸びます。あせらず復習しましょう。")

    st.markdown("#### 📈 あなたの成績")
    draw_stats()

    st.caption("← サイドバーのセットボタンから次の問題に挑戦できます。")


# ------------------------------------------------------------------
# 問題画面
# ------------------------------------------------------------------
def show_question():
    order = st.session_state.order
    i = st.session_state.index
    q = order[i]
    total = len(order)

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

    local_storage = LocalStorage()
    init_state(local_storage)

    # サイドバーを描く前に、終了したセットの達成率を記録しておく
    if st.session_state.get("finished"):
        record_result(local_storage)

    sidebar_controls(local_storage)

    if st.session_state.order is None:
        st.info("👈 左のサイドバーから出題セット（易・標準・難）を選ぶと、クイズが始まります。")
        st.markdown(
            f"- 各セットは**{SET_SIZE}問**ずつに分かれています\n"
            "- 答えを選ぶと、その場で正誤と解説が表示されます\n"
            "- 達成率は端末に保存され、次に開いたときも残ります"
        )
        st.markdown("#### 📈 あなたの成績")
        draw_stats()
    elif st.session_state.finished:
        show_result()
    else:
        show_question()


if __name__ == "__main__":
    main()
