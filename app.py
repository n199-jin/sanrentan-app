import streamlit as st
import sqlite3
import pandas as pd
import time

# --- データベース設定 ---
def init_db():
    conn = sqlite3.connect('sanrentan_v23.db', check_same_thread=False)
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
    return pd.read_sql_query("SELECT * FROM settings WHERE id=1", conn).iloc[0]

# --- UI設定 ---
st.set_page_config(page_title="三連単システム", layout="wide")

st.markdown("""
<style>
    .ans-card { text-align: center; padding: 30px; border-radius: 20px; color: white; font-weight: bold; margin: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }
    .gold { background: linear-gradient(135deg, #FFD700, #DAA520); color: black; font-size: 50px; border: 4px solid #FFF; }
    .silver { background: linear-gradient(135deg, #E0E0E0, #A0A0A0); color: black; font-size: 45px; border: 4px solid #FFF; }
    .bronze { background: linear-gradient(135deg, #CD7F32, #A0522D); color: white; font-size: 40px; border: 4px solid #FFF; }
    .option-box { text-align: center; background-color: #333; color: white; padding: 20px; border-radius: 12px; font-size: 28px; font-weight: bold; }
    .q-title { font-size: 55px !important; text-align: center; margin-bottom: 20px; font-weight: bold; }
    .score-banner { text-align: center; background: #FF4B4B; color: white; padding: 20px; border-radius: 15px; margin: 20px 0; border: 3px solid #FFF; }
</style>
""", unsafe_allow_html=True)

if 'admin_logged_in' not in st.session_state:
    st.session_state.admin_logged_in = False
if 'my_name' not in st.session_state:
    st.session_state.my_name = ""

conf = get_settings()
options_list = [opt.strip() for opt in conf['options'].split(',') if opt.strip()]
sync_key = f"{conf['is_open']}-{conf['current_q']}-{conf['show_ans']}-{conf['q_text']}"

st.sidebar.title("🎮 三連単")
mode = st.sidebar.radio("モード切替", ["参加者画面", "【投影用】メインモニター", "総合ランキング", "管理者画面"])

# --- 1. 参加者画面 ---
if mode == "参加者画面":
    st.markdown(f"### 第 {conf['current_q']} 問")
    st.title(conf['q_text'])
    st.divider()

    # ユーザー名がセッションにあるか確認
    my_answer = None
    if st.session_state.my_name:
        # 現在の問題番号(current_q)に紐づく自分の回答をDBから取得
        query = "SELECT * FROM scores WHERE q_id = ? AND name = ?"
        res = pd.read_sql_query(query, conn, params=(int(conf['current_q']), st.session_state.my_name))
        if not res.empty:
            my_answer = res.iloc[0]

    # --- 画面表示分岐 ---
    
    # 【正解発表モード】
    if conf['show_ans'] == 1:
        if my_answer is not None:
            st.markdown(f"""
            <div class="score-banner">
                <p style="margin:0; font-size:20px;">{st.session_state.my_name} さんの結果</p>
                <h1 style="margin:0; font-size:60px;">{my_answer['score']} 点</h1>
            </div>
            """, unsafe_allow_html=True)
            st.success(f"あなたの予想: 1位:{my_answer['g1']} / 2位:{my_answer['g2']} / 3位:{my_answer['g3']}")
        else:
            # ここが「回答していない」と出ていた部分。
            # セッションに名前があるのに回答がない場合は、送信ミスかDB反映遅延の可能性を考慮
            if st.session_state.my_name:
                st.warning(f"{st.session_state.my_name} さん、この問題（第{conf['current_q']}問）への回答が確認できませんでした。")
            else:
                st.info("名前を入力して参加してください。")

    # 【回答受付モード】
    elif conf['is_open'] == 1:
        if my_answer is not None:
            st.success(f"✅ 第{conf['current_q']}問の予想を送信済みです。発表までお待ちください。")
            st.info(f"あなたの予想: 1位:{my_answer['g1']} / 2位:{my_answer['g2']} / 3位:{my_answer['g3']}")
        else:
            with st.form("vote_form"):
                u_name = st.text_input("あなたの名前", value=st.session_state.my_name, placeholder="例：山田太郎")
                st.write("▼ 3位まで選んでください（重複不可）")
                c1, c2, c3 = st.columns(3)
                g1 = c1.selectbox("1位", ["未選択"] + options_list, key="p_g1")
                g2 = c2.selectbox("2位", ["未選択"] + options_list, key="p_g2")
                g3 = c3.selectbox("3位", ["未選択"] + options_list, key="p_g3")
                if st.form_submit_button("予想を送信"):
                    if u_name and "未選択" not in [g1, g2, g3] and len({g1, g2, g3}) == 3:
                        st.session_state.my_name = u_name
                        c = conn.cursor()
                        c.execute("INSERT OR IGNORE INTO users (name) VALUES (?)", (u_name,))
                        c.execute("INSERT OR REPLACE INTO scores (q_id, name, g1, g2, g3, score) VALUES (?, ?, ?, ?, ?, 0)", 
                                  (int(conf['current_q']), u_name, g1, g2, g3))
                        conn.commit()
                        st.rerun() # 送信後即座に画面を切り替えて「送信済み」にする
                    else:
                        st.error("名前の入力と、重複のない3つの選択をしてください。")

    # 【待機モード】（締め切り中かつ正解発表前）
    else:
        st.info("⌛ 現在、管理者が次の問題を準備中、または回答を締め切っています。")
        if st.session_state.my_name:
            st.write(f"参加者： {st.session_state.my_name} さん")

    # 3秒おきに自動更新
    time.sleep(3)
    if 'last_sync' not in st.session_state or st.session_state.last_sync != sync_key:
        st.session_state.last_sync = sync_key
        st.rerun()

# --- 2. 【投影用】メインモニター ---
elif mode == "【投影用】メインモニター":
    st.markdown(f"<h1 class='q-title'>{conf['q_text']}</h1>", unsafe_allow_html=True)
    st.divider()
    if conf['show_ans'] == 1:
        st.markdown("<h1 style='text-align: center; color: #FF4B4B; font-size: 80px;'>正解発表</h1>", unsafe_allow_html=True)
        st.markdown(f"<div class='ans-card gold'>1位：{conf['last_ans1']}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='ans-card silver'>2位：{conf['last_ans2']}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='ans-card bronze'>3位：{conf['last_ans3']}</div>", unsafe_allow_html=True)
    else:
        st.markdown("<h3 style='text-align:center;'>【 選択肢 】</h3>", unsafe_allow_html=True)
        cols = st.columns(len(options_list) if len(options_list) > 0 else 1)
        for i, opt in enumerate(options_list):
            cols[i].markdown(f"<div class='option-box'>{opt}</div>", unsafe_allow_html=True)
    time.sleep(3)
    st.rerun()

# --- 3. 総合ランキング ---
elif mode == "総合ランキング":
    st.title("📊 総合ランキング")
    df = pd.read_sql_query("SELECT name as 名前, SUM(score) as 合計 FROM scores GROUP BY name ORDER BY 合計 DESC", conn)
    st.table(df.head(20))
    time.sleep(10)
    st.rerun()

# --- 4. 管理者画面 ---
elif mode == "管理者画面":
    if not st.session_state.admin_logged_in:
        pwd = st.text_input("パスワード", type="password")
        if st.button("ログイン"):
            if pwd == "admin123": st.session_state.admin_logged_in = True; st.rerun()
    else:
        st.subheader("📢 進行管理")
        new_q = st.number_input("問題番号", value=int(conf['current_q']), min_value=1)
        new_txt = st.text_input("問題文", value=conf['q_text'])
        new_opts = st.text_area("選択肢（カンマ区切り）", value=conf['options'])
        status = st.radio("状態", ["締め切り", "受付中"], index=1 if conf['is_open'] == 1 else 0, horizontal=True)
        if st.button("設定を保存して全員の画面を更新"):
            # show_ans=0 にリセットすることで、次の問題の正解発表を隠す
            conn.cursor().execute("UPDATE settings SET current_q=?, q_text=?, options=?, is_open=?, show_ans=0 WHERE id=1", 
                                  (new_q, new_txt, new_opts, 1 if status == "受付中" else 0))
            conn.commit()
            st.success(f"第{new_q}問の設定を反映しました")
            st.rerun()

        st.divider()
        st.subheader("🎯 採点（締め切り時のみ可能）")
        if conf['is_open'] == 0:
            cur_q = int(conf['current_q'])
            df_q = pd.read_sql_query(f"SELECT name, g1, g2, g3 FROM scores WHERE q_id={cur_q}", conn)
            target = st.selectbox("回答読込", ["--"] + list(df_q['name']))
            iv = ["未選択"]*3
            if target != "--":
                row = df_q[df_q['name'] == target].iloc[0]
                iv = [row['g1'], row['g2'], row['g3']]
            
            c1, c2, c3 = st.columns(3)
            a1 = c1.selectbox("1位", ["未選択"] + options_list, index=(options_list.index(iv[0])+1) if iv[0] in options_list else 0)
            a2 = c2.selectbox("2位", ["未選択"] + options_list, index=(options_list.index(iv[1])+1) if iv[1] in options_list else 0)
            a3 = c3.selectbox("3位", ["未選択"] + options_list, index=(options_list.index(iv[2])+1) if iv[2] in options_list else 0)
            
            if st.button("採点実行（投影画面に正解を出す）"):
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
                conn.commit()
                st.success("採点が完了し、参加者の画面にも点数が表示されました。")
        else:
            st.info("「締め切り」にすると採点できます。")
