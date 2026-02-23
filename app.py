import streamlit as st
import sqlite3
import pandas as pd

# --- データベース設定 ---
def init_db():
    conn = sqlite3.connect('sanrentan.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS answers 
                 (name TEXT, rank1 TEXT, rank2 TEXT, rank3 TEXT, score INTEGER DEFAULT 0)''')
    conn.commit()
    return conn

conn = init_db()

# --- 得点計算ロジック ---
def calculate_score(correct, guess):
    if not correct or None in correct:
        return 0
    
    correct_set = set(correct)
    guess_set = set(guess)
    common_elements = correct_set & guess_set
    match_count = len(common_elements)

    if list(correct) == list(guess): return 6 # サンレンタン
    if match_count == 3: return 4            # サンレンプク
    if correct[0] == guess[0] and correct[1] == guess[1]: return 3 # ニレンタン
    if match_count == 2: return 2            # プクプク
    if correct[0] == guess[0]: return 1      # タン
    return 0

# --- UI設定 ---
st.set_page_config(page_title="サンレンタン大会システム", layout="wide")
st.title("🏆 サンレンタン集計システム")

tabs = st.tabs(["投票フォーム", "【管理者】集計・ランキング"])

# --- タブ1: 投票フォーム ---
with tabs[0]:
    st.header("回答を送信してください")
    with st.form("vote_form"):
        name = st.text_input("名前（ニックネーム可）", placeholder="例：田中")
        st.write("1位〜3位の選択肢を記入してください")
        c1, c2, c3 = st.columns(3)
        g1 = c1.text_input("1位", key="g1")
        g2 = c2.text_input("2位", key="g2")
        g3 = c3.text_input("3位", key="g3")
        
        submitted = st.form_submit_button("予想を送信")
        if submitted:
            if name and g1 and g2 and g3:
                c = conn.cursor()
                # 既存の回答があれば更新、なければ挿入
                c.execute("DELETE FROM answers WHERE name=?", (name,))
                c.execute("INSERT INTO answers (name, rank1, rank2, rank3) VALUES (?, ?, ?, ?)", 
                          (name, g1, g2, g3))
                conn.commit()
                st.success(f"{name}さんの予想を受付ました！")
            else:
                st.error("すべての項目を入力してください")

# --- タブ2: 管理者画面 ---
with tabs[1]:
    st.header("正解入力とランキング")
    with st.expander("正解（出題者の答え）を入力"):
        sc1, sc2, sc3 = st.columns(3)
        ans1 = sc1.text_input("正解1位", key="ans1")
        ans2 = sc2.text_input("正解2位", key="ans2")
        ans3 = sc3.text_input("正解3位", key="ans3")
        
        if st.button("全参加者のスコアを計算・更新"):
            correct_ans = [ans1, ans2, ans3]
            df_all = pd.read_sql_query("SELECT * FROM answers", conn)
            
            for index, row in df_all.iterrows():
                user_guess = [row['rank1'], row['rank2'], row['rank3']]
                new_score = calculate_score(correct_ans, user_guess)
                conn.cursor().execute("UPDATE answers SET score = ? WHERE name = ?", (new_score, row['name']))
            conn.commit()
            st.rerun()

    # ランキング表示
    st.subheader("現在のランキング")
    df_ranking = pd.read_sql_query("SELECT name, score, rank1, rank2, rank3 FROM answers ORDER BY score DESC", conn)
    if not df_ranking.empty:
        st.dataframe(df_ranking, use_container_width=True)
    else:
        st.info("まだ回答がありません")

    if st.button("全データをリセット"):
        conn.cursor().execute("DELETE FROM answers")
        conn.commit()
        st.warning("データを消去しました")
        st.rerun()