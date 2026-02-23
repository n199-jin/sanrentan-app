import streamlit as st
import sqlite3
import pandas as pd
import time

# --- データベース設定 ---
def init_db():
    conn = sqlite3.connect('sanrentan_v11.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (name TEXT PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS scores 
                 (q_id INTEGER, name TEXT, g1 TEXT, g2 TEXT, g3 TEXT, score INTEGER, 
                  PRIMARY KEY (q_id, name))''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings 
                 (id INTEGER PRIMARY KEY, options TEXT, is_open INTEGER, current_q INTEGER, 
                  last_ans1 TEXT, last_ans2 TEXT, last_ans3 TEXT, show_ans INTEGER DEFAULT 0)''')
    c.execute("""INSERT OR IGNORE INTO settings (id, options, is_open, current_q, last_ans1, last_ans2, last_ans3, show_ans) 
                 VALUES (1, 'A,B,C,D', 0, 1, '', '', '', 0)""")
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

def get_settings():
    return pd.read_sql_query("SELECT * FROM settings WHERE id=1", conn).iloc[0]

# --- UI設定 ---
st.set_page_config(page_title="サンレンタン・フルシステム", layout="wide")

if 'admin_logged_in' not in st.session_state:
    st.session_state.admin_logged_in = False

st.sidebar.title("🎮 メニュー")
mode = st.sidebar.radio("モード切替", ["参加者画面", "【投影用】問題・正解表示", "総合ランキング", "管理者画面"])

conf = get_settings()
options_list = [opt.strip() for opt in conf['options'].split(',') if opt.strip()]

# --- 1. 参加者画面 ---
if mode == "参加者画面":
    st.title(f"📝 第 {conf['current_q']} 問：予想投票")
    if conf['is_open'] == 1:
        st.success("🟢 現在、回答を受付中です！")
    else:
        st.error("🔴 現在、回答は締め切られています。")

    with st.form("vote_form"):
        name = st.text_input("あなたの名前（必須）")
        st.info(f"【選択肢】 {', '.join(options_list)}")
        c1, c2, c3 = st.columns(3)
        g1 = c1.selectbox("1位予想", ["未選択"] + options_list, key="g1")
        g2 = c2.selectbox("2位予想", ["未選択"] + options_list, key="g2")
        g3 = c3.selectbox("3位予想", ["未選択"] + options_list, key="g3")
        if st.form_submit_button("予想を送信"):
            if conf['is_open'] == 0:
                st.error("送信失敗：締め切り済みです。")
            elif name and g1 != "未選択" and g2 != "未選択" and g3 != "未選択":
                if len({g1, g2, g3}) < 3:
                    st.error("❌ 同じ選択肢は選べません！")
                else:
                    c = conn.cursor()
                    c.execute("INSERT OR IGNORE INTO users (name) VALUES (?)", (name,))
                    c.execute("INSERT OR REPLACE INTO scores (q_id, name, g1, g2, g3, score) VALUES (?, ?, ?, ?, ?, 0)", 
                              (int(conf['current_q']), name, g1, g2, g3))
                    conn.commit()
                    st.success(f"✅ 受理しました！")
                    st.balloons()
            else:
                st.error("⚠️ 入力不備があります。")

# --- 2. 【投影用】問題・正解表示画面 ---
elif mode == "【投影用】問題・正解表示":
    st.markdown(f"<h1 style='text-align: center; font-size: 60px;'>第 {conf['current_q']} 問</h1>", unsafe_allow_html=True)
    st.divider()
    
    # 選択肢の表示
    st.markdown("<h2 style='text-align: center;'>【 選択肢 】</h2>", unsafe_allow_html=True)
    cols = st.columns(len(options_list))
    for i, opt in enumerate(options_list):
        cols[i].markdown(f"<div style='text-align: center; background-color: #f0f2f6; padding: 20px; border-radius: 10px; font-size: 24px; font-weight: bold;'>{opt}</div>", unsafe_allow_html=True)
    
    st.divider()

    # 正解表示の演出
    if conf['show_ans'] == 1:
        st.markdown("<h1 style='text-align: center; color: #ff4b4b; font-size: 80px;'>正解発表！</h1>", unsafe_allow_html=True)
        a1, a2, a3 = st.columns(3)
        a1.metric("1位", conf['last_ans1'])
        a2.metric("2位", conf['last_ans2'])
        a3.metric("3位", conf['last_ans3'])
        st.balloons()
    else:
        st.markdown("<h2 style='text-align: center; color: gray;'>正解発表をお楽しみに...</h2>", unsafe_allow_html=True)

    if st.button("🔄 画面更新"):
        st.rerun()

# --- 3. 総合ランキング画面 ---
elif mode == "総合ランキング":
    st.title("📊 総合スコアランキング")
    if st.button("🔄 最新の情報に更新"):
        st.rerun()
    df_rank = pd.read_sql_query("SELECT name as 名前, SUM(score) as 合計点 FROM scores GROUP BY name ORDER BY 合計点 DESC, 名前 ASC", conn)
    st.table(df_rank.head(15)) 

# --- 4. 管理者画面 ---
elif mode == "管理者画面":
    st.title("⚙️ 管理者パネル")
    if not st.session_state.admin_logged_in:
        pwd = st.text_input("パスワード", type="password")
        if st.button("ログイン"):
            if pwd == "admin123": st.session_state.admin_logged_in = True; st.rerun()
    else:
        # 進行管理
        st.subheader("📢 進行管理")
        c_m1, c_m2 = st.columns(2)
        with c_m1:
            new_q = st.number_input("現在の問題番号", value=int(conf['current_q']), min_value=1)
            status = st.radio("受付状態", ["締め切り", "受付中"], index=1 if conf['is_open'] == 1 else 0)
            if st.button("進行設定を保存"):
                conn.cursor().execute("UPDATE settings SET current_q = ?, is_open = ?, show_ans = 0 WHERE id = 1", (new_q, 1 if status == "受付中" else 0))
                conn.commit(); st.rerun()
        with c_m2:
            new_opts = st.text_area("選択肢の編集", value=conf['options'])
            if st.button("選択肢を反映"):
                conn.cursor().execute("UPDATE settings SET options = ? WHERE id = 1", (new_opts,))
                conn.commit(); st.success("更新完了")

        st.divider()
        # 採点
        st.subheader("🎯 採点と集計")
        cur_q = int(conf['current_q'])
        df_ans = pd.read_sql_query(f"SELECT name, g1, g2, g3 FROM scores WHERE q_id={cur_q}", conn)
        target_user = st.selectbox("出題者の回答を読み込む", ["-- 選択 --"] + list(df_ans['name']))
        init_ans = ["未選択"] * 3
        if target_user != "-- 選択 --":
            u_row = df_ans[df_ans['name'] == target_user].iloc[0]
            init_ans = [u_row['g1'], u_row['g2'], u_row['g3']]

        sc1, sc2, sc3 = st.columns(3)
        ans1 = sc1.selectbox("正解1位", ["未選択"] + options_list, index=(options_list.index(init_ans[0])+1) if init_ans[0] in options_list else 0)
        ans2 = sc2.selectbox("正解2位", ["未選択"] + options_list, index=(options_list.index(init_ans[1])+1) if init_ans[1] in options_list else 0)
        ans3 = sc3.selectbox("正解3位", ["未選択"] + options_list, index=(options_list.index(init_ans[2])+1) if init_ans[2] in options_list else 0)

        if st.button("採点実行＆投影画面に正解を表示"):
            if "未選択" not in [ans1, ans2, ans3]:
                correct = [ans1, ans2, ans3]
                # スコア計算
                for _, row in df_ans.iterrows():
                    u_g = [row['g1'], row['g2'], row['g3']]
                    sc = calculate_score(correct, u_g)
                    conn.cursor().execute("UPDATE scores SET score=? WHERE q_id=? AND name=?", (sc, cur_q, row['name']))
                # 正解を設定テーブルに保存
                conn.cursor().execute("UPDATE settings SET last_ans1=?, last_ans2=?, last_ans3=?, show_ans=1 WHERE id=1", (ans1, ans2, ans3))
                conn.commit(); st.success("集計完了！投影画面を確認してください。")
            else:
                st.error("正解を選択してください")
