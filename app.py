import streamlit as st
import sqlite3
import pandas as pd
import time

# --- データベース設定 ---
def init_db():
    conn = sqlite3.connect('sanrentan_v20.db', check_same_thread=False)
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

def get_settings():
    # キャッシュを回避して最新の状態を取得
    return pd.read_sql_query("SELECT * FROM settings WHERE id=1", conn).iloc[0]

# --- UI設定 ---
st.set_page_config(page_title="三連単システム", layout="wide")

# CSS: 答えを巨大かつ見やすく
st.markdown("""
<style>
    .ans-card { text-align: center; padding: 40px; border-radius: 20px; color: white; font-weight: bold; margin: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }
    .gold { background: linear-gradient(135deg, #FFD700, #DAA520); color: black; font-size: 60px; border: 5px solid #FFF; }
    .silver { background: linear-gradient(135deg, #E0E0E0, #A0A0A0); color: black; font-size: 55px; border: 5px solid #FFF; }
    .bronze { background: linear-gradient(135deg, #CD7F32, #A0522D); color: white; font-size: 50px; border: 5px solid #FFF; }
    .option-box { text-align: center; background-color: #333; color: white; padding: 25px; border-radius: 12px; font-size: 32px; font-weight: bold; border: 1px solid #555; }
    .q-title { font-size: 80px !important; text-align: center; margin-bottom: 30px; font-weight: bold; color: #FFF; text-shadow: 2px 2px 4px #000; }
</style>
""", unsafe_allow_html=True)

# 管理用ログイン状態
if 'admin_logged_in' not in st.session_state:
    st.session_state.admin_logged_in = False

# 現在のDB設定を取得
conf = get_settings()
options_list = [opt.strip() for opt in conf['options'].split(',') if opt.strip()]

# 自動更新用のキー（状態が変わったら rerun するための識別子）
sync_key = f"{conf['is_open']}-{conf['current_q']}-{conf['show_ans']}-{conf['q_text']}"

st.sidebar.title("🎮 メニュー")
mode = st.sidebar.radio("モード切替", ["参加者画面", "【投影用】メインモニター", "総合ランキング", "管理者画面"])

# --- 1. 参加者画面 ---
if mode == "参加者画面":
    st.markdown(f"<p style='color:gray;'>第 {conf['current_q']} 問</p>", unsafe_allow_html=True)
    st.markdown(f"## {conf['q_text']}")
    st.divider()

    if conf['is_open'] == 1:
        st.success("🟢 回答受付中")
        # フォームを使用
        with st.form("vote_form"):
            name = st.text_input("名前（必須）")
            c1, c2, c3 = st.columns(3)
            g1 = c1.selectbox("1位", ["未選択"] + options_list)
            g2 = c2.selectbox("2位", ["未選択"] + options_list)
            g3 = c3.selectbox("3位", ["未選択"] + options_list)
            
            submit = st.form_submit_button("予想を送信")
            if submit:
                if name and "未選択" not in [g1, g2, g3] and len({g1, g2, g3}) == 3:
                    c = conn.cursor()
                    c.execute("INSERT OR IGNORE INTO users (name) VALUES (?)", (name,))
                    c.execute("INSERT OR REPLACE INTO scores (q_id, name, g1, g2, g3, score) VALUES (?, ?, ?, ?, ?, 0)", 
                              (int(conf['current_q']), name, g1, g2, g3))
                    conn.commit()
                    st.toast("送信が完了しました！")
                else:
                    st.error("入力に不備があります（重複不可）")
    else:
        st.error("🔴 現在、回答は締め切られています。次の問題までお待ちください。")

    # 参加者画面の自動更新ロジック（3秒おき）
    time.sleep(3)
    if 'last_sync_participant' not in st.session_state or st.session_state.last_sync_participant != sync_key:
        st.session_state.last_sync_participant = sync_key
        st.rerun()

# --- 2. 【投影用】メインモニター ---
elif mode == "【投影用】メインモニター":
    if conf['show_ans'] == 1:
        # 正解発表時：問題文と答えのみ
        st.markdown(f"<h1 class='q-title'>{conf['q_text']}</h1>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center; color: #FF4B4B; font-size: 90px; margin-bottom: 20px;'>正解発表</h1>", unsafe_allow_html=True)
        st.markdown(f"<div class='ans-card gold'>1位：{conf['last_ans1']}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='ans-card silver'>2位：{conf['last_ans2']}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='ans-card bronze'>3位：{conf['last_ans3']}</div>", unsafe_allow_html=True)
    else:
        # 出題中：問題文と選択肢
        st.markdown(f"<p style='text-align:center; font-size:40px; color:gray;'>第 {conf['current_q']} 問</p>", unsafe_allow_html=True)
        st.markdown(f"<h1 class='q-title'>{conf['q_text']}</h1>", unsafe_allow_html=True)
        st.divider()
        st.markdown("<h2 style='text-align: center; margin-bottom: 20px;'>【 選択肢 】</h2>", unsafe_allow_html=True)
        cols = st.columns(len(options_list) if len(options_list) > 0 else 1)
        for i, opt in enumerate(options_list):
            cols[i].markdown(f"<div class='option-box'>{opt}</div>", unsafe_allow_html=True)

    time.sleep(3)
    st.rerun()

# --- 3. 総合ランキング ---
elif mode == "総合ランキング":
    st.title("📊 リアルタイムランキング")
    df = pd.read_sql_query("SELECT name as 名前, SUM(score) as 合計 FROM scores GROUP BY name ORDER BY 合計 DESC", conn)
    st.table(df.head(20))
    time.sleep(10)
    st.rerun()

# --- 4. 管理者画面 ---
elif mode == "管理者画面":
    if not st.session_state.admin_logged_in:
        pwd = st.text_input("管理者パスワード", type="password")
        if st.button("ログイン"):
            if pwd == "admin123": st.session_state.admin_logged_in = True; st.rerun()
    else:
        st.subheader("📢 進行管理")
        new_q = st.number_input("問題番号", value=int(conf['current_q']))
        new_txt = st.text_input("問題文", value=conf['q_text'])
        new_opts = st.text_area("選択肢（カンマ区切り）", value=conf['options'])
        status = st.radio("受付状態", ["締め切り", "受付中"], index=1 if conf['is_open'] == 1 else 0, horizontal=True)
        if st.button("設定を反映（全員の画面が更新されます）"):
            conn.cursor().execute("UPDATE settings SET current_q=?, q_text=?, options=?, is_open=?, show_ans=0 WHERE id=1", 
                                  (new_q, new_txt, new_opts, 1 if status == "受付中" else 0))
            conn.commit(); st.success("設定を更新しました！"); time.sleep(1); st.rerun()

        st.divider()
        st.subheader("🎯 採点")
        if conf['is_open'] == 0:
            cur_q = int(conf['current_q'])
            df_q = pd.read_sql_query(f"SELECT name, g1, g2, g3 FROM scores WHERE q_id={cur_q}", conn)
            target = st.selectbox("出題者の回答を読み込む", ["-- 手動選択 --"] + list(df_q['name']))
            
            iv = ["未選択"] * 3
            if target != "-- 手動選択 --":
                row = df_q[df_q['name'] == target].iloc[0]
                iv = [row['g1'], row['g2'], row['g3']]
            
            c1, c2, c3 = st.columns(3)
            a1 = c1.selectbox("1位正解", ["未選択"] + options_list, index=(options_list.index(iv[0])+1) if iv[0] in options_list else 0)
            a2 = c2.selectbox("2位正解", ["未選択"] + options_list, index=(options_list.index(iv[1])+1) if iv[1] in options_list else 0)
            a3 = c3.selectbox("3位正解", ["未選択"] + options_list, index=(options_list.index(iv[2])+1) if iv[2] in options_list else 0)
            
            if st.button("採点実行（投影画面に発表）"):
                if "未選択" not in [a1, a2, a3]:
                    def calc(c, g):
                        if c == g: return 6
                        m = len(set(c) & set(g))
                        if m == 3: return 4
                        if c[0] == g[0] and c[1] == g[1]: return 3
                        if m == 2: return 2
                        if c[0] == g[0]: return 1
                        return 0
                    
                    for _, r in df_q.iterrows():
                        sc = calc([a1, a2, a3], [r['g1'], r['g2'], r['g3']])
                        conn.cursor().execute("UPDATE scores SET score=? WHERE q_id=? AND name=?", (sc, cur_q, r['name']))
                    conn.cursor().execute("UPDATE settings SET last_ans1=?, last_ans2=?, last_ans3=?, show_ans=1 WHERE id=1", (a1, a2, a3))
                    conn.commit(); st.success("採点が完了しました！")
                else: st.error("正解をすべて選択してください")
        else:
            st.info("「締め切り」状態にすると採点パネルが出ます。")
