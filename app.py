"""統計検定2級 クイズアプリ（Streamlit）

使い方:
    streamlit run app.py
"""

import json
import random

import altair as alt
import pandas as pd
import streamlit as st
from streamlit_local_storage import LocalStorage

from questions import QUESTIONS

st.set_page_config(page_title="統計検定2級 クイズ", page_icon="📊", layout="centered")

SET_SIZE = 5  # 1セットあたりの問題数
LEVELS = ["易", "標準", "難"]  # 難易度の表示順
LEVEL_BADGE = {"易": "🟢", "標準": "🟡", "難": "🔴"}
STORAGE_KEY = "toukei2kyuu_results"  # 端末（localStorage）に保存するキー


def level_of(label):
    """セットのラベル（例: 標準3）から難易度（標準）を取り出す。"""
    for lv in LEVELS:
        if label.startswith(lv):
            return lv
    return None


def medal(avg):
    """平均達成率に応じた達成バッジ（メダル）を返す。"""
    if avg >= 80:
        return "🥇 金メダル"
    if avg >= 60:
        return "🥈 銀メダル"
    return "🥉 銅メダル"


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


def draw_progress_chart():
    """セットごとの達成率（正解率）を棒グラフで表示する。"""
    results = st.session_state.get("results", {})
    labels = all_set_labels()
    data = pd.DataFrame(
        {"達成率(%)": [results.get(label, 0) for label in labels]},
        index=labels,
    )
    st.bar_chart(data, y="達成率(%)", height=260)

    if results:
        avg = sum(results.values()) / len(results)
        st.caption(
            f"挑戦したセット: {len(results)} / {len(labels)} ｜ "
            f"挑戦したセットの平均達成率: {avg:.0f}%"
        )
    else:
        st.caption("セットを解くと、ここに達成率が記録されていきます。")


def draw_level_summary():
    """難易度ごとの平均達成率と達成バッジを表示する。"""
    results = st.session_state.get("results", {})
    labels = all_set_labels()
    cols = st.columns(len(LEVELS))
    for col, lv in zip(cols, LEVELS):
        lv_labels = [la for la in labels if level_of(la) == lv]
        vals = [results[la] for la in lv_labels if la in results]
        title = f"{LEVEL_BADGE[lv]} {lv}"
        if vals:
            avg = sum(vals) / len(vals)
            col.metric(title, f"{avg:.0f}%", f"{len(vals)}/{len(lv_labels)} セット")
            badge = medal(avg)
            # その難易度を全セット制覇していたら王冠を付ける
            if len(vals) == len(lv_labels):
                badge += "・👑全制覇"
            col.caption(badge)
        else:
            col.metric(title, "—", "未挑戦")


def draw_completion_pie():
    """挑戦済み／未挑戦のセット数を円グラフで表示する。"""
    results = st.session_state.get("results", {})
    total = len(all_set_labels())
    done = len(results)
    pie_df = pd.DataFrame(
        {"状態": ["挑戦済み", "未挑戦"], "セット数": [done, total - done]}
    )
    chart = (
        alt.Chart(pie_df)
        .mark_arc(innerRadius=50)
        .encode(
            theta=alt.Theta("セット数:Q"),
            color=alt.Color(
                "状態:N",
                scale=alt.Scale(
                    domain=["挑戦済み", "未挑戦"], range=["#4C9BE8", "#E0E0E0"]
                ),
                legend=alt.Legend(title=None),
            ),
            tooltip=["状態", "セット数"],
        )
        .properties(height=240)
    )
    st.altair_chart(chart, use_container_width=True)
    st.caption(f"進み具合: {done} / {total} セット完了")


def draw_stats():
    """成績ダッシュボード（難易度サマリ・円グラフ・棒グラフ）をまとめて表示する。"""
    results = st.session_state.get("results", {})
    total = len(all_set_labels())

    # 全セット制覇のお知らせ
    if results and len(results) == total:
        st.success("🎉 全12セット制覇！コンプリートおめでとうございます！")

    st.markdown("##### 難易度ごとの達成率")
    draw_level_summary()

    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown("##### 進み具合")
        draw_completion_pie()
    with c2:
        st.markdown("##### セットごとの達成率")
        draw_progress_chart()


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
        for i, s in enumerate(sets):
            if st.sidebar.button(
                f"セット{i + 1}（{len(s)}問）",
                use_container_width=True,
                key=f"set_{level}_{i}",
            ):
                start_quiz(s, label=f"{level}{i + 1}")
                st.rerun()

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
def show_result(local_storage):
    total = len(st.session_state.order)
    score = st.session_state.score
    rate = score / total * 100 if total else 0

    # このセットの達成率を記録し、端末（localStorage）にも保存する
    label = st.session_state.get("current_set")
    if label and not st.session_state.get("result_saved"):
        st.session_state.results[label] = rate
        local_storage.setItem(STORAGE_KEY, json.dumps(st.session_state.results))
        st.session_state.result_saved = True
        # 全セット制覇した瞬間だけ風船を飛ばす
        if len(st.session_state.results) == len(all_set_labels()):
            st.balloons()

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

    local_storage = LocalStorage()
    init_state(local_storage)
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
        show_result(local_storage)
    else:
        show_question()


if __name__ == "__main__":
    main()
