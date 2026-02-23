import streamlit as st
import sqlite3
import pandas as pd
import time

# --- データベース設定 ---
def init_db():
    conn = sqlite3.connect('sanrentan_v30.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (name TEXT PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS scores 
                 (q_id INTEGER, name TEXT, g1 TEXT, g2 TEXT, g3 TEXT, score INTEGER, 
                  PRIMARY KEY (q_id, name))''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings 
                 (id INTEGER PRIMARY KEY, options TEXT, is_open INTEGER, current_q INTEGER, 
                  last_ans1 TEXT, last_ans2 TEXT, last_ans3 TEXT, show_ans INTEGER, q_text TEXT)''')
    c.execute("""INSERT OR IGNORE INTO settings (id, options, is_open, current_q, last_ans1, last_ans2, last_ans3, show_ans, q_text) 
                 VALUES (1, 'A,B,C,D,E', 0, 1, '', '', '', 0, '問題文を入力してください')""")
    conn.commit()
    return conn

conn = init_db()

def get_yaku_name(score):
    if score == 6: return "✨ サンレンタン（ピタリ）"
    if score == 4: return "🔥 サンレンプク（順個人的中）"
    if score == 3: return "⚡ 1-2位的中"
    if score == 2: return "✅ 2つ的中（順不同）"
    if score == 1: return "🎯 1位的中"
    return "残念..."

def get_settings():
    return pd.read_sql_query("SELECT * FROM settings WHERE id=1", conn).iloc[0]

# --- UI設定 ---
st.set_page_config(page_title="サンレンタンシステム", layout="wide")
st.markdown("""
<style>
    .main { background-color: #0E1117; }
    header {visibility: hidden;} footer {visibility: hidden;}
    .ans-card { text-align: center; padding: 30px; border-radius: 20px; color: white; font-weight: bold; margin: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.5); }
    .gold { background: linear-gradient(135deg, #FFD700, #DAA520); color: black; font-size: 55px; border: 4px solid #FFF; }
    .silver { background: linear-gradient(135deg, #E0E0E0, #A0A0A0); color: black; font-size: 50px; border: 4px solid #FFF; }
    .bronze { background: linear-gradient(135deg, #CD7F32, #A0522D); color: white; font-size: 45px; border: 4px solid #FFF; }
    .option-box { text-align: center; background-color: #1F2937; color: white; padding: 25px; border-radius: 12px; font-size: 32px; font-weight: bold; border: 2px solid #374151; }
    .q-title { font-size: 70px !important; text-align: center; margin-bottom: 30px; font-weight: bold; color: white; }
    .score-banner { text-align: center; background: #FF4B4B; color: white; padding: 30px; border-radius: 20px; margin: 20px 0; border: 4px solid #FFF; }
</style>
""", unsafe_allow_html=True)

# URLパラメータ取得
params = st.query_params
if 'my_name' not in st.session_state:
    st.session_state.my_name = params.get("user", "")

conf = get_settings()
options_list = [opt.strip() for opt in conf['options'].split(',') if opt.strip()]
sync_key = f"{conf['is_open']}-{conf['current_q']}-{conf['show_ans']}-{conf['q_text']}"

# --- サイドバー ---
st.sidebar.title("🎮 サンレンタン")
# モードのリストを固定。ランキングはここには出さない。
mode = st.sidebar.radio("モード切替", ["参加者画面", "【投影用】メインモニター", "管理者画面"])

# 特殊な「ランキング表示」状態かどうかを判定
show_ranking = params.get("page") == "rank"

# --- 画面描画ロジック ---

# 1. ランキング表示（管理者ボタン経由のみ）
if show_ranking:
    st.header("📊 総合ランキング")
    df_rank = pd.read_sql_query("SELECT name as 名前, SUM(score) as 合計 FROM scores WHERE name != '模範解答' GROUP BY name ORDER BY 合計 DESC", conn)
    st.table(df_rank.head(50))
    if st.button("管理者画面に戻る"):
        st.query_params.clear() # パラメータを消してリロード
        st.rerun()
    time.sleep(10)
    st.rerun()

# 2. 参加者画面
elif mode == "参加者画面":
    with st.empty().container():
        st.markdown(f"### 第 {conf['current_q']} 問")
        st.title(conf['q_text'])
        st.divider()
        my_answer = None
        if st.session_state.my_name:
            res = pd.read_sql_query("SELECT * FROM scores WHERE q_id = ? AND name = ?", conn, params=(int(conf['current_q']), st.session_state.my_name))
            if not res.empty: my_answer = res.iloc[0]

        if conf['show_ans'] == 1:
            if my_answer is not None:
                yaku = get_yaku_name(my_answer['score'])
                st.markdown(f"""<div class="score-banner"><p style="margin:0; font-size:24px;">{st.session_state.my_name} さんの結果</p><h1 style="margin:0; font-size:70px;">{my_answer['score']} 点</h1><span style="font-size:30px; font-weight:bold; color:#FFD700;">{yaku}</span></div>""", unsafe_allow_html=True)
            else: st.info("この問題への回答がありません。")
        elif conf['is_open'] == 1:
            if my_answer is not None:
                st.success(f"✅ 第{conf['current_q']}問 送信済み")
                st.info(f"予想: 1位:{my_answer['g1']} / 2位:{my_answer['g2']} / 3位:{my_answer['g3']}")
            else:
                with st.form("vote_form"):
                    u_name = st.text_input("名前", value=st.session_state.my_name)
                    c1, c2, c3 = st.columns(3)
                    g1 = c1.selectbox("1位", ["未選択"] + options_list)
                    g2 = c2.selectbox("2位", ["未選択"] + options_list)
                    g3 = c3.selectbox("3位", ["未選択"] + options_list)
                    if st.form_submit_button("送信"):
                        if u_name and "未選択" not in [g1, g2, g3] and len({g1, g2, g3}) == 3:
                            st.session_state.my_name = u_name
                            st.query_params["user"] = u_name
                            conn.cursor().execute("INSERT OR REPLACE INTO scores (q_id, name, g1, g2, g3, score) VALUES (?, ?, ?, ?, ?, 0)", (int(conf['current_q']), u_name, g1, g2, g3))
                            conn.commit(); st.rerun()
        else: st.info("⌛ 次の問題を準備中...")
    time.sleep(3)
    if st.session_state.get('last_sync') != sync_key:
        st.session_state.last_sync = sync_key
        st.rerun()

# 3. 【投影用】メインモニター
elif mode == "【投影用】メインモニター":
    with st.empty().container():
        if conf['show_ans'] == 1:
            st.markdown(f"<h1 class='q-title'>{conf['q_text']}</h1>", unsafe_allow_html=True)
            st.markdown("<h1 style='text-align: center; color: #FF4B4B; font-size: 90px; margin-top:-20px;'>正解</h1>", unsafe_allow_html=True)
            st.markdown(f"<div class='ans-card gold'>1位：{conf['last_ans1']}</div><div class='ans-card silver'>2位：{conf['last_ans2']}</div><div class='ans-card bronze'>3位：{conf['last_ans3']}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<h1 class='q-title'>{conf['q_text']}</h1>", unsafe_allow_html=True)
            st.divider()
            cols = st.columns(len(options_list) if len(options_list) > 0 else 1)
            for i, opt in enumerate(options_list):
                cols[i].markdown(f"<div class='option-box'>{opt}</div>", unsafe_allow_html=True)
    time.sleep(3); st.rerun()

# 4. 管理者画面
elif mode == "管理者画面":
    if not st.session_state.get('admin_logged_in', False):
        pwd = st.text_input("パスワード", type="password")
        if st.button("ログイン"):
            if pwd == "admin123": st.session_state.admin_logged_in = True; st.rerun()
    else:
        st.success("管理者ログイン中")
        if st.button("🏆 総合ランキングを表示（別画面）"):
            st.query_params["page"] = "rank"
            st.rerun()
        
        st.divider()
        st.subheader("📢 進行管理")
        new_q = st.number_input("問題番号", value=int(conf['current_q']), min_value=1)
        new_txt = st.text_input("問題文", value=conf['q_text'])
        new_opts = st.text_area("選択肢", value=conf['options'])
        status = st.radio("状態", ["締め切り", "受付中"], index=1 if conf['is_open'] == 1 else 0, horizontal=True)
        if st.button("反映"):
            conn.cursor().execute("UPDATE settings SET current_q=?, q_text=?, options=?, is_open=?, show_ans=0 WHERE id=1", (new_q, new_txt, new_opts, 1 if status == "受付中" else 0))
            conn.commit(); st.rerun()

        st.divider()
        if conf['is_open'] == 0:
            st.subheader("🎯 採点")
            df_q = pd.read_sql_query(f"SELECT name, g1, g2, g3 FROM scores WHERE q_id={conf['current_q']}", conn)
            target = st.selectbox("出題者選択", ["-- 手動 --"] + list(df_q['name']))
            iv = ["未選択"]*3
            if target != "-- 手動 --":
                row = df_q[df_q['name'] == target].iloc[0]
                iv = [row['g1'], row['g2'], row['g3']]
            c1, c2, c3 = st.columns(3)
            a1 = c1.selectbox("1位", ["未選択"] + options_list, index=(options_list.index(iv[0])+1) if iv[0] in options_list else 0)
            a2 = c2.selectbox("2位", ["未選択"] + options_list, index=(options_list.index(iv[1])+1) if iv[1] in options_list else 0)
            a3 = c3.selectbox("3位", ["未選択"] + options_list, index=(options_list.index(iv[2])+1) if iv[2] in options_list else 0)
            if st.button("採点確定"):
                conn.cursor().execute("INSERT OR REPLACE INTO scores (q_id, name, g1, g2, g3, score) VALUES (?, '模範解答', ?, ?, ?, 0)", (int(conf['current_q']), a1, a2, a3))
                def calc(c, g):
                    if c == g: return 6
                    m = len(set(c) & set(g)); return 4 if m == 3 else (3 if c[0]==g[0] and c[1]==g[1] else (2 if m == 2 else (1 if c[0]==g[0] else 0)))
                all_resp = pd.read_sql_query(f"SELECT name, g1, g2, g3 FROM scores WHERE q_id={conf['current_q']}", conn)
                for _, r in all_resp.iterrows():
                    sc = calc([a1, a2, a3], [r['g1'], r['g2'], r['g3']])
                    conn.cursor().execute("UPDATE scores SET score=? WHERE q_id=? AND name=?", (sc, int(conf['current_q']), r['name']))
                conn.cursor().execute("UPDATE settings SET last_ans1=?, last_ans2=?, last_ans3=?, show_ans=1 WHERE id=1", (a1, a2, a3))
                conn.commit(); st.rerun()

        st.divider()
        st.subheader("🚨 危険な操作")
        confirm = st.checkbox("全回答データを削除し、最初からやり直すことに同意します")
        if st.button("全データをリセット", disabled=not confirm):
            conn.cursor().execute("DELETE FROM scores")
            conn.cursor().execute("DELETE FROM users")
            conn.cursor().execute("UPDATE settings SET current_q=1, is_open=0, show_ans=0, last_ans1='', last_ans2='', last_ans3='' WHERE id=1")
            conn.commit(); st.warning("リセット完了"); st.rerun()
