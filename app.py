import streamlit as st
import sqlite3
import pandas as pd
import time

# --- データベース設定 ---
def init_db():
    conn = sqlite3.connect('sanrentan_v17.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (name TEXT PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS scores 
                 (q_id INTEGER, name TEXT, g1 TEXT, g2 TEXT, g3 TEXT, score INTEGER, 
                  PRIMARY KEY (q_id, name))''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings 
                 (id INTEGER PRIMARY KEY, options TEXT, is_open INTEGER, current_q INTEGER, 
                  last_ans1 TEXT, last_ans2 TEXT, last_ans3 TEXT, show_ans INTEGER, q_text TEXT)''')
    c.execute("""INSERT OR IGNORE INTO settings (id, options, is_open, current_q, last_ans1, last_ans2, last_ans3, show_ans, q_text) 
                 VALUES (1, 'A,B,C,D,E', 0, 1, '', '', '', 0, 'ここに問題文を入力してください')""")
    conn.commit()
    return conn

conn = init_db()

def calculate_score(correct, guess):
    if not all(correct) or not all(guess) or "未選択" in correct or "未選択" in guess: return 0
    c_list, g_list = list(correct), list(guess)
    match_count = len(set(c_list) & set(g_list))
    if c_list == g_list: return 6
    if match_count == 3: return 4
    if c_list[0] == g_list[0] and c_list[1] == g_list[1]: return 3
    if match_count == 2: return 2
    if c_list[0] == g_list[0]: return 1
    return 0

def get_settings():
    return pd.read_sql_query("SELECT * FROM settings WHERE id=1", conn).iloc[0]

# --- UI設定 ---
st.set_page_config(page_title="サンレンタン・フルシステム", layout="wide")

if 'last_status' not in st.session_state:
    st.session_state.last_status = None
if 'admin_logged_in' not in st.session_state:
    st.session_state.admin_logged_in = False

st.sidebar.title("🎮 メニュー")
mode = st.sidebar.radio("モード切替", ["参加者画面", "【投影用】問題・正解表示", "総合ランキング", "管理者画面"])

conf = get_settings()
options_list = [opt.strip() for opt in conf['options'].split(',') if opt.strip()]
current_status_str = f"{conf['is_open']}-{conf['current_q']}-{conf['show_ans']}"

# --- 1. 参加者画面 ---
if mode == "参加者画面":
    st.markdown(f"### 第 {conf['current_q']} 問")
    st.title(conf['q_text'])
    
    if conf['is_open'] == 1:
        st.success("🟢 現在、回答を受付中です！")
        with st.form("vote_form"):
            name = st.text_input("あなたの名前（必須）")
            c1, c2, c3 = st.columns(3)
            g1 = c1.selectbox("1位予想", ["未選択"] + options_list)
            g2 = c2.selectbox("2位予想", ["未選択"] + options_list)
            g3 = c3.selectbox("3位予想", ["未選択"] + options_list)
            if st.form_submit_button("予想を送信"):
                if name and "未選択" not in [g1, g2, g3] and len({g1, g2, g3}) == 3:
                    c = conn.cursor()
                    c.execute("INSERT OR IGNORE INTO users (name) VALUES (?)", (name,))
                    c.execute("INSERT OR REPLACE INTO scores (q_id, name, g1, g2, g3, score) VALUES (?, ?, ?, ?, ?, 0)", 
                              (int(conf['current_q']), name, g1, g2, g3))
                    conn.commit()
                    st.success("✅ 受理しました！")
                    st.balloons()
                else:
                    st.error("入力内容に不備があります（重複不可）")
    else:
        st.error("🔴 現在、回答は締め切られています。")

    time.sleep(5)
    if st.session_state.last_status != current_status_str:
        st.session_state.last_status = current_status_str
        st.rerun()

# --- 2. 【投影用】問題・正解表示画面 ---
elif mode == "【投影用】問題・正解表示":
    st.markdown(f"<p style='text-align: center; font-size: 50px; color: gray;'>第 {conf['current_q']} 問</p>", unsafe_allow_html=True)
    st.markdown(f"<h1 style='text-align: center; font-size: 80px;'>{conf['q_text']}</h1>", unsafe_allow_html=True)
    st.divider()
    
    st.markdown("<p style='text-align: center; font-size: 30px;'>【 選 択 肢 】</p>", unsafe_allow_html=True)
    cols = st.columns(len(options_list) if len(options_list) > 0 else 1)
    for i, opt in enumerate(options_list):
        cols[i].markdown(f"""
            <div style='text-align: center; background-color: #1E1E1E; color: #FFFFFF; 
            padding: 20px 10px; border-radius: 15px; font-size: 35px; font-weight: bold; 
            border: 3px solid #4B4B4B; box-shadow: 2px 2px 5px rgba(0,0,0,0.3);'>
            {opt}
            </div>
        """, unsafe_allow_html=True)
    
    if conf['show_ans'] == 1:
        st.markdown("<h1 style='text-align: center; color: #ff4b4b; font-size: 100px; margin-top: 30px;'>正解発表！</h1>", unsafe_allow_html=True)
        a1, a2, a3 = st.columns(3)
        a1.metric("🏆 1位", conf['last_ans1'])
        a2.metric("🥈 2位", conf['last_ans2'])
        a3.metric("🥉 3位", conf['last_ans3'])
        st.balloons()

    time.sleep(5)
    st.rerun()

# --- 3. 総合ランキング画面 ---
elif mode == "総合ランキング":
    st.title("📊 総合スコアランキング")
    df_rank = pd.read_sql_query("SELECT name as 名前, SUM(score) as 合計点 FROM scores GROUP BY name ORDER BY 合計点 DESC, 名前 ASC", conn)
    st.table(df_rank.head(20))
    time.sleep(10)
    st.rerun()

# --- 4. 管理者画面 ---
elif mode == "管理者画面":
    if not st.session_state.admin_logged_in:
        pwd = st.text_input("管理者パスワード", type="password")
        if st.button("ログイン"):
            if pwd == "admin123":
                st.session_state.admin_logged_in = True
                st.rerun()
            else: st.error("パスワードが違います")
    else:
        st.subheader("📢 進行管理")
        c_m1, c_m2 = st.columns(2)
        with c_m1:
            new_q = st.number_input("問題番号", value=int(conf['current_q']))
            new_txt = st.text_input("問題文", value=conf['q_text'])
            status = st.radio("受付状態", ["締め切り", "受付中"], index=1 if conf['is_open'] == 1 else 0)
            if st.button("進行設定を保存"):
                conn.cursor().execute("UPDATE settings SET current_q=?, q_text=?, is_open=?, show_ans=0 WHERE id=1", (new_q, new_txt, 1 if status == "受付中" else 0))
                conn.commit(); st.rerun()
        with c_m2:
            new_opts = st.text_area("選択肢(カンマ区切り)", value=conf['options'])
            if st.button("選択肢のみ更新"):
                conn.cursor().execute("UPDATE settings SET options=? WHERE id=1", (new_opts,))
                conn.commit(); st.success("更新完了")

        st.divider()
        st.subheader("🎯 採点")
        if conf['is_open'] == 1:
            st.warning("⚠️ 「締め切り」にして保存してから採点してください。")
        else:
            cur_q = int(conf['current_q'])
            df_q = pd.read_sql_query(f"SELECT name, g1, g2, g3 FROM scores WHERE q_id={cur_q}", conn)
            
            # --- エラー修正箇所 ---
            target_user = st.selectbox("出題者の回答読込", ["-- 手動 --"] + list(df_q['name']))
            
            # 初期値の決定ロジックを安全に変更
            init_vals = ["未選択", "未選択", "未選択"]
            if target_user != "-- 手動 --":
                selected_row = df_q[df_q['name'] == target_user]
                if not selected_row.empty:
                    init_vals = [selected_row.iloc[0]['g1'], selected_row.iloc[0]['g2'], selected_row.iloc[0]['g3']]
            
            sc1, sc2, sc3 = st.columns(3)
            ans1 = sc1.selectbox("正解1位", ["未選択"] + options_list, index=(options_list.index(init_vals[0])+1) if init_vals[0] in options_list else 0)
            ans2 = sc2.selectbox("正解2位", ["未選択"] + options_list, index=(options_list.index(init_vals[1])+1) if init_vals[1] in options_list else 0)
            ans3 = sc3.selectbox("正解3位", ["未選択"] + options_list, index=(options_list.index(init_vals[2])+1) if init_vals[2] in options_list else 0)

            if st.button("採点実行＆投影画面に表示"):
                if "未選択" not in [ans1, ans2, ans3]:
                    correct = [ans1, ans2, ans3]
                    for _, row in df_q.iterrows():
                        sc = calculate_score(correct, [row['g1'], row['g2'], row['g3']])
                        conn.cursor().execute("UPDATE scores SET score=? WHERE q_id=? AND name=?", (sc, cur_q, row['name']))
                    conn.cursor().execute("UPDATE settings SET last_ans1=?, last_ans2=?, last_ans3=?, show_ans=1 WHERE id=1", (ans1, ans2, ans3))
                    conn.commit(); st.success("採点完了！"); st.balloons()
                else: st.error("正解を選択してください")
