import streamlit as st
import sqlite3
import pandas as pd
import time

# --- データベース設定 ---
def init_db():
    conn = sqlite3.connect('sanrentan_v18.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (name TEXT PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS scores 
                 (q_id INTEGER, name TEXT, g1 TEXT, g2 TEXT, g3 TEXT, score INTEGER, 
                  PRIMARY KEY (q_id, name))''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings 
                 (id INTEGER PRIMARY KEY, options TEXT, is_open INTEGER, current_q INTEGER, 
                  last_ans1 TEXT, last_ans2 TEXT, last_ans3 TEXT, show_ans INTEGER, q_text TEXT)''')
    c.execute("""INSERT OR IGNORE INTO settings (id, options, is_open, current_q, last_ans1, last_ans2, last_ans3, show_ans, q_text) 
                 VALUES (1, 'A,B,C,D,E', 0, 1, '', '', '', 0, '問題文をここに入力')""")
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
    # 常に最新状態を取得するため、キャッシュを使わずにSQLを実行
    df = pd.read_sql_query("SELECT * FROM settings WHERE id=1", conn)
    return df.iloc[0]

# --- UI設定 ---
st.set_page_config(page_title="サンレンタン・フルシステム", layout="wide")

# カスタムCSSでUIを微調整
st.markdown("""
<style>
    .option-card {
        text-align: center; background-color: #262730; color: white; 
        padding: 25px 10px; border-radius: 15px; font-size: 32px; 
        font-weight: bold; border: 2px solid #4B4B4B; margin-bottom: 10px;
    }
    .main-title { font-size: 50px !important; font-weight: 800; text-align: center; }
</style>
""", unsafe_allow_html=True)

if 'last_status_key' not in st.session_state:
    st.session_state.last_status_key = None
if 'admin_logged_in' not in st.session_state:
    st.session_state.admin_logged_in = False

# サイドバー
st.sidebar.title("🎮 三連単システム")
mode = st.sidebar.radio("メニュー", ["参加者画面", "【投影用】メインモニター", "総合ランキング", "管理者画面"])

conf = get_settings()
options_list = [opt.strip() for opt in conf['options'].split(',') if opt.strip()]
current_status_key = f"{conf['is_open']}-{conf['current_q']}-{conf['show_ans']}"

# --- 1. 参加者画面 ---
if mode == "参加者画面":
    st.markdown(f"<p style='text-align:center; color:gray;'>Question {conf['current_q']}</p>", unsafe_allow_html=True)
    st.markdown(f"<h1 style='text-align:center;'>{conf['q_text']}</h1>", unsafe_allow_html=True)
    st.divider()
    
    if conf['is_open'] == 1:
        st.info("🟢 回答受付中（送信するまで自動更新されません）")
        with st.form("vote_form"):
            name = st.text_input("あなたの名前", placeholder="入力してください")
            st.write("▼ 予想順位を選択")
            c1, c2, c3 = st.columns(3)
            g1 = c1.selectbox("1位", ["未選択"] + options_list)
            g2 = c2.selectbox("2位", ["未選択"] + options_list)
            g3 = c3.selectbox("3位", ["未選択"] + options_list)
            
            if st.form_submit_button("この内容で送信する"):
                if name and "未選択" not in [g1, g2, g3] and len({g1, g2, g3}) == 3:
                    c = conn.cursor()
                    c.execute("INSERT OR IGNORE INTO users (name) VALUES (?)", (name,))
                    c.execute("INSERT OR REPLACE INTO scores (q_id, name, g1, g2, g3, score) VALUES (?, ?, ?, ?, ?, 0)", 
                              (int(conf['current_q']), name, g1, g2, g3))
                    conn.commit()
                    st.toast(f"第{conf['current_q']}問 受理完了！", icon="✅")
                else:
                    st.error("入力不備（重複や未選択）があります。")
    else:
        st.error("🔴 現在、回答は締め切られています。画面が切り替わるまでお待ちください。")

    # 3秒おきに「受付状態」のみチェックし、変化があれば即座にリロード
    time.sleep(3)
    if st.session_state.last_status_key != current_status_key:
        st.session_state.last_status_key = current_status_key
        st.rerun()

# --- 2. 【投影用】メインモニター ---
elif mode == "【投影用】メインモニター":
    st.markdown(f"<p style='text-align:center; font-size:40px; color:gray;'>第 {conf['current_q']} 問</p>", unsafe_allow_html=True)
    st.markdown(f"<h1 class='main-title'>{conf['q_text']}</h1>", unsafe_allow_html=True)
    st.divider()
    
    # カード型の選択肢表示
    st.markdown("<p style='text-align:center; font-size:25px;'>【 選択肢 】</p>", unsafe_allow_html=True)
    cols = st.columns(len(options_list) if len(options_list) > 0 else 1)
    for i, opt in enumerate(options_list):
        cols[i].markdown(f"<div class='option-card'>{opt}</div>", unsafe_allow_html=True)
    
    if conf['show_ans'] == 1:
        st.markdown("<h1 style='text-align:center; color:#ff4b4b; font-size:80px; margin-top:30px;'>正解発表！</h1>", unsafe_allow_html=True)
        a1, a2, a3 = st.columns(3)
        a1.metric("🏆 1位", conf['last_ans1'])
        a2.metric("🥈 2位", conf['last_ans2'])
        a3.metric("🥉 3位", conf['last_ans3'])
    
    time.sleep(4)
    st.rerun()

# --- 3. 総合ランキング ---
elif mode == "総合ランキング":
    st.title("📊 総合スコアランキング")
    df_rank = pd.read_sql_query("SELECT name as 名前, SUM(score) as 合計点 FROM scores GROUP BY name ORDER BY 合計点 DESC, 名前 ASC", conn)
    st.table(df_rank.head(20))
    time.sleep(10)
    st.rerun()

# --- 4. 管理者画面 ---
elif mode == "管理者画面":
    if not st.session_state.admin_logged_in:
        pwd = st.text_input("パスワード", type="password")
        if st.button("ログイン"):
            if pwd == "admin123": st.session_state.admin_logged_in = True; st.rerun()
    else:
        # レイアウトを2列に分けて整理
        tab1, tab2 = st.tabs(["📢 進行・問題設定", "🎯 採点と集計"])
        
        with tab1:
            st.subheader("問題の管理")
            new_q = st.number_input("問題番号", value=int(conf['current_q']))
            new_txt = st.text_input("問題文（タイトル）", value=conf['q_text'])
            new_opts = st.text_area("選択肢（カンマ区切り）", value=conf['options'])
            status = st.radio("現在の状態", ["締め切り", "受付中"], index=1 if conf['is_open'] == 1 else 0, horizontal=True)
            
            if st.button("設定を保存し、投影画面を更新"):
                conn.cursor().execute("UPDATE settings SET current_q=?, q_text=?, options=?, is_open=?, show_ans=0 WHERE id=1", 
                                      (new_q, new_txt, new_opts, 1 if status == "受付中" else 0))
                conn.commit()
                st.toast("設定を保存しました。")
                time.sleep(1)
                st.rerun()

        with tab2:
            st.subheader("採点")
            if conf['is_open'] == 1:
                st.warning("⚠️ 「締め切り」状態にすると採点パネルが表示されます。")
            else:
                cur_q = int(conf['current_q'])
                df_q = pd.read_sql_query(f"SELECT name, g1, g2, g3 FROM scores WHERE q_id={cur_q}", conn)
                
                target_user = st.selectbox("出題者の名前を選択（回答を読み込む）", ["-- 手動選択 --"] + list(df_q['name']))
                
                # 読み込みロジックの修正
                init_v = ["未選択"] * 3
                if target_user != "-- 手動選択 --":
                    sel = df_q[df_q['name'] == target_user]
                    if not sel.empty:
                        init_v = [sel.iloc[0]['g1'], sel.iloc[0]['g2'], sel.iloc[0]['g3']]
                
                c1, c2, c3 = st.columns(3)
                ans1 = c1.selectbox("正解1位", ["未選択"] + options_list, index=(options_list.index(init_v[0])+1) if init_v[0] in options_list else 0)
                ans2 = c2.selectbox("正解2位", ["未選択"] + options_list, index=(options_list.index(init_v[1])+1) if init_v[1] in options_list else 0)
                ans3 = c3.selectbox("正解3位", ["未選択"] + options_list, index=(options_list.index(init_v[2])+1) if init_v[2] in options_list else 0)

                if st.button("採点確定＆結果を投影"):
                    if "未選択" not in [ans1, ans2, ans3]:
                        correct = [ans1, ans2, ans3]
                        for _, row in df_q.iterrows():
                            sc = calculate_score(correct, [row['g1'], row['g2'], row['g3']])
                            conn.cursor().execute("UPDATE scores SET score=? WHERE q_id=? AND name=?", (sc, cur_q, row['name']))
                        conn.cursor().execute("UPDATE settings SET last_ans1=?, last_ans2=?, last_ans3=?, show_ans=1 WHERE id=1", (ans1, ans2, ans3))
                        conn.commit()
                        st.success("採点が完了しました。投影画面に正解が表示されています。")
                    else:
                        st.error("正解をすべて選択してください。")
