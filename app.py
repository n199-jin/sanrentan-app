import streamlit as st
import sqlite3
import pandas as pd

# --- データベース設定 ---
def init_db():
    conn = sqlite3.connect('sanrentan_v2.db', check_same_thread=False)
    c = conn.cursor()
    # 回答用テーブル
    c.execute('''CREATE TABLE IF NOT EXISTS answers 
                 (name TEXT PRIMARY KEY, rank1 TEXT, rank2 TEXT, rank3 TEXT, score INTEGER DEFAULT 0)''')
    # 選択肢・設定用テーブル
    c.execute('''CREATE TABLE IF NOT EXISTS settings 
                 (id INTEGER PRIMARY KEY, options TEXT, ans1 TEXT, ans2 TEXT, ans3 TEXT)''')
    # 初期データ投入
    c.execute("INSERT OR IGNORE INTO settings (id, options) VALUES (1, 'A,B,C,D')")
    conn.commit()
    return conn

conn = init_db()

# --- 得点計算ロジック ---
def calculate_score(correct, guess):
    if not all(correct) or not all(guess): return 0
    correct_set, guess_set = set(correct), set(guess)
    match_count = len(correct_set & guess_set)

    if list(correct) == list(guess): return 6
    if match_count == 3: return 4
    if correct[0] == guess[0] and correct[1] == guess[1]: return 3
    if match_count == 2: return 2
    if correct[0] == guess[0]: return 1
    return 0

# --- アプリUI ---
st.set_page_config(page_title="サンレンタン・プロ", layout="wide")
st.title("🏆 サンレンタン大会システム")

# 最新の設定を取得
def get_settings():
    return pd.read_sql_query("SELECT * FROM settings WHERE id=1", conn).iloc[0]

settings = get_settings()
options_list = [opt.strip() for opt in settings['options'].split(',') if opt.strip()]

tabs = st.tabs(["投票フォーム", "【管理者】設定・ランキング"])

# --- タブ1: 投票フォーム ---
with tabs[0]:
    if not options_list:
        st.warning("管理者が選択肢を設定するまでお待ちください。")
    else:
        with st.form("vote_form"):
            name = st.text_input("名前（必須）")
            st.info(f"選択肢から予想を選んでください: {', '.join(options_list)}")
            c1, c2, c3 = st.columns(3)
            g1 = c1.selectbox("1位", ["未選択"] + options_list, key="g1")
            g2 = c2.selectbox("2位", ["未選択"] + options_list, key="g2")
            g3 = c3.selectbox("3位", ["未選択"] + options_list, key="g3")
            
            if st.form_submit_button("予想を送信"):
                if name and g1 != "未選択" and g2 != "未選択" and g3 != "未選択":
                    if len({g1, g2, g3}) < 3:
                        st.error("同じ選択肢は選べません！")
                    else:
                        c = conn.cursor()
                        c.execute("INSERT OR REPLACE INTO answers (name, rank1, rank2, rank3, score) VALUES (?, ?, ?, ?, 0)", 
                                  (name, g1, g2, g3))
                        conn.commit()
                        st.success(f"受付完了！ 正解発表をお待ちください。")
                else:
                    st.error("名前の入力と3つの選択を完了させてください。")

# --- タブ2: 管理者画面 ---
with tabs[1]:
    # 1. 選択肢の設定
    st.header("1. お題（選択肢）の設定")
    new_options = st.text_area("選択肢をカンマ(,)区切りで入力してください", value=settings['options'])
    if st.button("選択肢を更新"):
        conn.cursor().execute("UPDATE settings SET options = ? WHERE id = 1", (new_options,))
        conn.commit()
        st.success("選択肢を更新しました！参加者画面に反映されます。")
        st.rerun()

    st.divider()

    # 2. 正解入力と集計
    st.header("2. 正解発表と集計")
    sc1, sc2, sc3 = st.columns(3)
    ans1 = sc1.selectbox("正解1位", ["未選択"] + options_list)
    ans2 = sc2.selectbox("正解2位", ["未選択"] + options_list)
    ans3 = sc3.selectbox("正解3位", ["未選択"] + options_list)
    
    if st.button("全参加者のスコアを一括計算"):
        if ans1 != "未選択" and ans2 != "未選択" and ans3 != "未選択":
            correct_ans = [ans1, ans2, ans3]
            df_all = pd.read_sql_query("SELECT * FROM answers", conn)
            for _, row in df_all.iterrows():
                u_guess = [row['rank1'], row['rank2'], row['rank3']]
                score = calculate_score(correct_ans, u_guess)
                conn.cursor().execute("UPDATE answers SET score = ? WHERE name = ?", (score, row['name']))
            conn.commit()
            st.success("計算完了！ランキングを更新しました。")
            st.rerun()
        else:
            st.error("正解をすべて選択してください。")

    # 3. ランキング
    st.divider()
    st.header("3. 結果ランキング")
    df_ranking = pd.read_sql_query("SELECT name, score, rank1, rank2, rank3 FROM answers ORDER BY score DESC, name ASC", conn)
    st.dataframe(df_ranking, use_container_width=True)

    if st.button("全データ（回答のみ）をリセット"):
        conn.cursor().execute("DELETE FROM answers")
        conn.commit()
        st.warning("参加者の回答データをリセットしました。")
        st.rerun()
