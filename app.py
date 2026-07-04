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
STORAGE_KEY = "toukei2kyuu_results"  # 達成率を端末（localStorage）に保存するキー
RESUME_KEY = "toukei2kyuu_resume"    # 中断したセットの「しおり」を保存するキー


def build_sets(level, size=SET_SIZE):
    """ある難易度の問題を、並び順に size 問ずつのセットに分ける。"""
    qs = [q for q in QUESTIONS if q["level"] == level]
    return [qs[i : i + size] for i in range(0, len(qs), size)]


def all_sets():
    """全セットを表示順に（ラベル, 問題リスト）のペアで返す。"""
    sets = []
    for level in LEVELS:
        for i, s in enumerate(build_sets(level)):
            sets.append((f"{level}{i + 1}", s))
    return sets


def all_set_labels():
    """全セットのラベル（例: 易1, 標準3, 難1）を表示順で返す。"""
    return [label for label, _ in all_sets()]


def set_by_label(label):
    """ラベル（例: 標準3）からそのセットの問題リストを返す。なければ None。"""
    for lbl, qs in all_sets():
        if lbl == label:
            return qs
    return None


def draw_stats():
    """成績ダッシュボード（全制覇のお知らせと案内）を表示する。"""
    results = st.session_state.get("results", {})
    total = len(all_set_labels())

    # 全セット制覇のお知らせ
    if results and len(results) == total:
        st.success(f"🎉 全{total}セット制覇！コンプリートおめでとうございます！")

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
    if "resume" not in st.session_state:
        # 中断したセットの「しおり」を読み込む（なければ None）
        raw = local_storage.getItem(RESUME_KEY)
        try:
            st.session_state.resume = json.loads(raw) if raw else None
        except (ValueError, TypeError):
            st.session_state.resume = None


def start_quiz(question_pool, label=None, shuffle=False, start_index=0, start_score=0):
    """選んだ問題でクイズを始める。start_index/start_score を指定すると途中から再開できる。"""
    pool = list(question_pool)
    if shuffle:
        random.shuffle(pool)
    st.session_state.order = pool
    st.session_state.current_set = label  # いま挑戦中のセット名
    st.session_state.index = start_index  # 今が何問目か（再開時はその位置から）
    st.session_state.score = start_score  # 正解数（再開時はそれまでの分を引き継ぐ）
    st.session_state.answered = False   # 現在の問題に回答済みか
    st.session_state.selected = None    # 選んだ選択肢
    st.session_state.finished = False   # 全問終わったか
    st.session_state.result_saved = False  # 結果を保存済みか
    st.session_state.reviews = {}       # 問題id → 正誤・選んだ答え の記録
    # 前のセットで開いた解説をすべて閉じる（問題ごとのキーを消す）
    for k in [k for k in st.session_state if str(k).startswith("show_expl_")]:
        del st.session_state[k]


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
            # ボタンの上にそのセットの達成率を表示する
            if label in results:
                rate = results[label]
                st.sidebar.progress(rate / 100, text=f"達成率 {rate:.0f}%")
            else:
                st.sidebar.caption("　未挑戦")
            if st.sidebar.button(
                f"セット{i + 1}（{len(s)}問）",
                use_container_width=True,
                key=f"set_{level}_{i}",
            ):
                start_quiz(s, label=label)
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
    # このセットを最後まで解いたら、同じセットのしおりは用済みなので消す
    resume = st.session_state.get("resume")
    if resume and resume.get("label") == label:
        st.session_state.resume = None
        local_storage.setItem(RESUME_KEY, json.dumps(None))
    # 全セット制覇した瞬間だけ風船を飛ばす
    if len(st.session_state.results) == len(all_set_labels()):
        st.balloons()


def show_result():
    order = st.session_state.order
    total = len(order)
    score = st.session_state.score
    rate = score / total * 100 if total else 0
    label = st.session_state.get("current_set")
    reviews = st.session_state.get("reviews", {})

    st.subheader("🎉 おつかれさまでした！")
    set_name = f"（{label}）" if label else ""
    st.metric(f"スコア{set_name}", f"{score} / {total}", f"{rate:.0f}%")

    if rate >= 80:
        st.success("すばらしい！合格圏内のレベルです。")
    elif rate >= 60:
        st.info("あと少し！まちがえた分野を復習しましょう。")
    else:
        st.warning("やさしい問題（易）から見直すと伸びます。あせらず復習しましょう。")

    # 各問題の正誤一覧を表示する
    st.markdown("#### 📋 結果一覧")
    wrong_qs = []  # 間違えた問題（再挑戦用）
    for idx, q in enumerate(order, start=1):
        title = q["question"]
        if len(title) > 30:
            title = title[:30] + "…"
        r = reviews.get(q["id"])
        if r is None:
            st.markdown(f"{idx}. ⬜ 未回答　{title}")
        elif r["correct"]:
            st.markdown(f"{idx}. ✅ {title}")
        else:
            wrong_qs.append(q)
            st.markdown(f"{idx}. ❌ {title}　→ 正解: {q['choices'][q['answer']]}")

    # 間違えた問題だけをもう一度解き直すボタン
    if wrong_qs:
        if st.button(
            f"🔁 間違えた問題をもう一度（{len(wrong_qs)}問）",
            use_container_width=True,
        ):
            # 達成率には影響しない練習モードとして解き直す（label は付けない）
            start_quiz(wrong_qs, label=None)
            st.rerun()
    else:
        st.success("全問正解！このセットは完璧です 🎉")

    st.markdown("#### 📈 あなたの成績")
    draw_stats()

    st.caption("← サイドバーのセットボタンから次の問題に挑戦できます。")


# ------------------------------------------------------------------
# 問題画面
# ------------------------------------------------------------------
def stop_for_today(local_storage, next_index):
    """『今日はここまで』：次回このセットの続き（next_index 番目）から始められるよう
    しおりを保存してホームに戻る。練習モード（ラベルなし）では何もしない。"""
    label = st.session_state.get("current_set")
    if not label:
        return
    resume = {
        "label": label,
        "index": next_index,          # 次回このセットで最初に解く問題の位置
        "score": st.session_state.score,  # ここまでの正解数を引き継ぐ
    }
    st.session_state.resume = resume
    local_storage.setItem(RESUME_KEY, json.dumps(resume))
    st.session_state.order = None     # ホームに戻って中断する
    st.rerun()


def show_question(local_storage):
    order = st.session_state.order
    i = st.session_state.index
    q = order[i]
    total = len(order)

    badge = LEVEL_BADGE.get(q["level"], "")
    st.caption(f"分野: {q['category']} ｜ 難易度: {badge} {q['level']}")

    # 問題文の上の小さなボタン：答えずに先へ進める（スコアには影響しない）
    if not st.session_state.answered:
        if i + 1 < total:
            if st.button("次の問題を見る"):
                st.session_state.index += 1
                st.rerun()
        else:
            # セット最後の問題では、次のセットの先頭へ移動できる
            # （途中で移動してもセットは終了扱いにならず、達成率は保存されない）
            sets = all_sets()
            labels = [label for label, _ in sets]
            current = st.session_state.get("current_set")
            if current in labels and current != labels[-1]:
                next_label, next_qs = sets[labels.index(current) + 1]
                if st.button("次のセットの問題を見る"):
                    start_quiz(next_qs, label=next_label)
                    st.rerun()

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
            # あとで結果一覧に出せるよう、正誤を問題ごとに記録する
            st.session_state.setdefault("reviews", {})[q["id"]] = {
                "selected": selected,
                "correct": selected == q["answer"],
            }
            st.rerun()

        # 回答するボタンの下の小さなボタン：クリックしたときだけ解説を表示
        # 解説（st.info）と同じ水色に見えるようCSSで色を合わせる
        st.markdown(
            """
            <style>
            .st-key-show_expl_btn button {
                background-color: rgba(28, 131, 225, 0.1);
                color: rgb(0, 66, 128);
                border: 1px solid rgba(28, 131, 225, 0.4);
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        # 解説の表示・非表示は問題ごとに管理する（他の問題に影響しない）
        expl_key = f"show_expl_{q['id']}"
        if st.button("解説を見る", key="show_expl_btn"):
            st.session_state[expl_key] = True
        if st.session_state.get(expl_key):
            st.info(f"💡 解説: {q['explanation']}")

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

        if i + 1 < total:
            # 「次の問題へ」の隣に「🌙今日はここまで」を並べる（練習モードでは次の問題へのみ）
            if st.session_state.get("current_set"):
                col_next, col_stop = st.columns(2)
                next_clicked = col_next.button("次の問題へ", use_container_width=True)
                stop_clicked = col_stop.button("🌙 今日はここまで", use_container_width=True)
            else:
                next_clicked = st.button("次の問題へ", use_container_width=True)
                stop_clicked = False
            if next_clicked:
                st.session_state.answered = False
                st.session_state.selected = None
                st.session_state.index += 1
                st.rerun()
            if stop_clicked:
                # 次の問題から次回再開する
                stop_for_today(local_storage, i + 1)
        else:
            if st.button("結果を見る", use_container_width=True):
                st.session_state.answered = False
                st.session_state.selected = None
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
        # 中断したセットがあれば、続きから再開できるボタンを出す
        resume = st.session_state.get("resume")
        if resume and set_by_label(resume.get("label")) is not None:
            qs = set_by_label(resume["label"])
            remaining = len(qs) - resume["index"]
            if remaining > 0:
                st.success(
                    f"🌙 前回は「{resume['label']}」を途中で終了しました。"
                    f"続きから始められます（残り{remaining}問）。"
                )
                if st.button("▶️ 前回の続きから始める", use_container_width=True):
                    start_quiz(
                        qs,
                        label=resume["label"],
                        start_index=resume["index"],
                        start_score=resume["score"],
                    )
                    st.session_state.resume = None
                    local_storage.setItem(RESUME_KEY, json.dumps(None))
                    st.rerun()

        st.info("👈 左のサイドバーから出題セット（易・標準・難・実践）を選ぶと、クイズが始まります。")
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
        show_question(local_storage)


if __name__ == "__main__":
    main()
