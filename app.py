import streamlit as st
import sqlite3
import pandas as pd
import time

# --- データベース設定 ---
def init_db():
    conn = sqlite3.connect('sanrentan_v5.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (name TEXT PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS scores 
                 (q_id INTEGER, name TEXT, g1 TEXT, g2 TEXT, g3 TEXT, score INTEGER, 
                  PRIMARY KEY (q_id, name))''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings 
                 (id INTEGER PRIMARY KEY, options TEXT, is_open INTEGER, current_q INTEGER)''')
    c.execute("INSERT OR IGNORE INTO settings (id, options, is_open, current_q) VALUES (1, 'A,B,C,D', 0, 1)")
    conn.commit()
    return conn

conn = init_db()

# --- 得点計算ロジック ---
def calculate_score(correct, guess):
    if not all(correct) or not all(guess) or "未選択" in correct or "未選択" in guess: return 0
    correct_set, guess_set = set(correct), set(guess)
    match_count = len(correct_set & guess_set)
    if list(correct) == list(guess): return 6
    if match_count == 3: return 4
    if correct[0] == guess[0] and correct[1] == guess[1]: return 3
    if match_count == 2: return 2
    if correct[0] == guess[0]: return 1
    return 0

# --- データ取得 ---
def get_settings():
    return pd.read_sql_query("SELECT * FROM settings WHERE id=1", conn).iloc[0]

# --- UI設定 ---
st.set_page_config(page_title="サンレンタン・フルシステム", layout="wide")
conf = get_settings()
options_list = [opt.strip() for opt in conf['options'].split(',') if opt.strip()]

st.sidebar.title("🎮 メニュー")
mode = st.sidebar.radio("モード切替", ["参加者画面", "総合ランキング", "管理者画面"])

# --- 1. 参加者画面 ---
if mode == "参加者画面":
    st.title(f"📝 第 {conf['current_q']} 問：予想投票")
    
    if conf['is_open'] == 0:
        st.warning("🔒 現在、回答は締め切られています。")
    else:
        with st.form("vote_form"):
            name = st.text_input("あなたの名前（必須）")
            st.info(f"【選択肢】 {', '.join(options_list)}")
            c1, c2, c3 = st.columns(3)
            g1 = c1.selectbox("1位予想", ["未選択"] + options_list, key="g1")
            g2 = c2.selectbox("2位予想", ["未選択"] + options_list, key="g2")
            g3 = c3.selectbox("3位予想", ["未選択"] + options_list, key="g3")
            
            if st.form_submit_button("予想を送信"):
                if name and g1 != "未選択" and g2 != "未選択" and g3 != "未選択":
                    if len({g1, g2, g3}) < 3:
                        st.error("❌ 同じ選択肢は選べません！")
                    else:
                        c = conn.cursor()
                        c.execute("INSERT OR IGNORE INTO users (name) VALUES (?)", (name,))
                        c.execute("INSERT OR REPLACE INTO scores (q_id, name, g1, g2, g3, score) VALUES (?, ?, ?, ?, ?, 0)", 
                                  (int(conf['current_q']), name, g1, g2, g3))
                        conn.commit()
                        st.success(f"✅ {name}さんの回答を受理しました！")
                        st.balloons() # 送信成功の演出
                else:
                    st.error("⚠️ 名前と3つの順位をすべて選んでください。")

# --- 2. 総合ランキング画面 ---
elif mode == "総合ランキング":
    st.title("📊 総合スコアランキング")
    query = "SELECT name as 名前, SUM(score) as 合計点 FROM scores GROUP BY name ORDER BY 合計点 DESC, 名前 ASC"
    df_rank = pd.read_sql_query(query, conn)
    
    if not df_rank.empty:
        # 上位3名を強調表示する簡易表
        st.table(df_rank.head(10)) 
        with st.expander("🔍 全問題の回答・得点詳細"):
            df_all = pd.read_sql_query("SELECT q_id as 問, name as 名前, score as 点数 FROM scores ORDER BY q_id DESC", conn)
            st.dataframe(df_all, use_container_width=True)
    else:
        st.info("まだ集計データがありません。")

# --- 3. 管理者画面 ---
elif mode == "管理者画面":
    st.title("⚙️ 管理者専用パネル")
    if st.sidebar.text_input("パスワード", type="password") == "admin123":
        
        # 1. ステータス管理
        st.subheader("📢 進行管理")
        col1, col2 = st.columns(2)
        with col1:
            new_q = st.number_input("現在の問題番号", value=int(conf['current_q']), min_value=1)
            status = st.radio("回答受付状態", ["締め切り", "受付中"], index=1 if conf['is_open'] == 1 else 0)
            if st.button("設定を保存・更新"):
                is_open = 1 if status == "受付中" else 0
                conn.cursor().execute("UPDATE settings SET current_q = ?, is_open = ? WHERE id = 1", (new_q, is_open))
                conn.commit()
                st.toast(f"第{new_q}問を「{status}」にしました！") # 右下に通知
                time.sleep(1)
                st.rerun()

        with col2:
            new_opts = st.text_area("選択肢の編集（カンマ区切り）", value=conf['options'])
            if st.button("選択肢を反映"):
                conn.cursor().execute("UPDATE settings SET options = ? WHERE id = 1", (new_opts,))
                conn.commit()
                st.success("✅ 選択肢を更新しました。")
                st.rerun()

        st.divider()

        # 2. 採点
        st.subheader("🎯 採点と集計")
        st.write(f"第 {conf['current_q']} 問の正解を入力してください。")
        sc1, sc2, sc3 = st.columns(3)
        ans1 = sc1.selectbox("正解1位", ["未選択"] + options_list)
        ans2 = sc2.selectbox("正解2位", ["未選択"] + options_list)
        ans3 = sc3.selectbox("正解3位", ["未選択"] + options_list)
        
        if st.button("採点を実行する"):
            if "未選択" not in [ans1, ans2, ans3]:
                with st.spinner('集計中...'): # 処理中のぐるぐる表示
                    correct = [ans1, ans2, ans3]
                    cur_q = int(conf['current_q'])
                    df_q = pd.read_sql_query(f"SELECT * FROM scores WHERE q_id={cur_q}", conn)
                    for _, row in df_q.iterrows():
                        u_guess = [row['g1'], row['g2'], row['g3']]
                        sc = calculate_score(correct, u_guess)
                        conn.cursor().execute("UPDATE scores SET score=? WHERE q_id=? AND name=?", (sc, cur_q, row['name']))
                    conn.commit()
                    time.sleep(1) # 演出のための待ち
                st.success(f"✨ 第 {cur_q} 問の集計が完了しました！")
                st.balloons() # 採点完了の演出
            else:
                st.error("⚠️ 正解をすべて選択してください。")

        # 3. リセット
        st.divider()
        if st.checkbox("データ消去モードを有効にする"):
            if st.button("全回答・スコアを完全に消去"):
                c = conn.cursor()
                c.execute("DELETE FROM users"); c.execute("DELETE FROM scores")
                c.execute("UPDATE settings SET current_q=1, is_open=0 WHERE id=1")
                conn.commit()
                st.warning("💥 すべてのデータが削除されました。")
                st.rerun()
    else:
        st.info("左側のサイドバーにパスワードを入力してください。")
