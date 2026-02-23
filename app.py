import streamlit as st
import sqlite3
import pandas as pd
import time

# --- データベース設定 ---
def init_db():
    conn = sqlite3.connect('sanrentan_v15.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (name TEXT PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS scores 
                 (q_id INTEGER, name TEXT, g1 TEXT, g2 TEXT, g3 TEXT, score INTEGER, 
                  PRIMARY KEY (q_id, name))''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings 
                 (id INTEGER PRIMARY KEY, options TEXT, is_open INTEGER, current_q INTEGER, 
                  last_ans1 TEXT, last_ans2 TEXT, last_ans3 TEXT, show_ans INTEGER, q_text TEXT)''')
    # 初期データ。show_ans=0, is_open=0（締め切り）で開始
    c.execute("""INSERT OR IGNORE INTO settings (id, options, is_open, current_q, last_ans1, last_ans2, last_ans3, show_ans, q_text) 
                 VALUES (1, 'A,B,C,D,E', 0, 1, '', '', '', 0, 'ここに問題文を入力してください')""")
    conn.commit()
    return conn

conn = init_db()

# --- 得点計算ロジック ---
def calculate_score(correct, guess):
    if not all(correct) or not all(guess) or "未選択" in correct or "未選択" in guess: return 0
    c_list, g_list = list(correct), list(guess)
    match_count = len(set(c_list) & set(g_list))
    if c_list == g_list: return 6            # 3つ全て的中（順序一致）
    if match_count == 3: return 4           # 3つ全て的中（順序不問）
    if c_list[0] == g_list[0] and c_list[1] == g_list[1]: return 3 # 1,2位的中
    if match_count == 2: return 2           # 2つ的中（順序不問）
    if c_list[0] == g_list[0]: return 1     # 1位のみ的中
    return 0

def get_settings():
    return pd.read_sql_query("SELECT * FROM settings WHERE id=1", conn).iloc[0]

# --- UI設定 ---
st.set_page_config(page_title="サンレンタン・フルシステム", layout="wide")

if 'admin_logged_in' not in st.session_state:
    st.session_state.admin_logged_in = False

# サイドバーメニュー
st.sidebar.title("🎮 メニュー")
mode = st.sidebar.radio("モード切替", ["参加者画面", "【投影用】問題・正解表示", "総合ランキング", "管理者画面"])

conf = get_settings()
options_list = [opt.strip() for opt in conf['options'].split(',') if opt.strip()]

# --- 1. 参加者画面 ---
if mode == "参加者画面":
    st.markdown(f"<p style='color: gray; margin-bottom: 0;'>第 {conf['current_q']} 問</p>", unsafe_allow_html=True)
    st.title(conf['q_text'])
    
    if conf['is_open'] == 1:
        st.success("🟢 現在、回答を受付中です！")
        with st.form("vote_form"):
            name = st.text_input("あなたの名前（必須）", placeholder="例：山田 太郎")
            st.info(f"【選択肢】 {', '.join(options_list)}")
            c1, c2, c3 = st.columns(3)
            g1 = c1.selectbox("1位予想", ["未選択"] + options_list, key="g1")
            g2 = c2.selectbox("2位予想", ["未選択"] + options_list, key="g2")
            g3 = c3.selectbox("3位予想", ["未選択"] + options_list, key="g3")
            
            if st.form_submit_button("予想を送信"):
                if name and "未選択" not in [g1, g2, g3]:
                    if len({g1, g2, g3}) < 3:
                        st.error("❌ 同じ選択肢は選べません！")
                    else:
                        c = conn.cursor()
                        c.execute("INSERT OR IGNORE INTO users (name) VALUES (?)", (name,))
                        c.execute("INSERT OR REPLACE INTO scores (q_id, name, g1, g2, g3, score) VALUES (?, ?, ?, ?, ?, 0)", 
                                  (int(conf['current_q']), name, g1, g2, g3))
                        conn.commit()
                        st.success(f"✅ {name}さんの第{conf['current_q']}問の回答を受理しました！")
                        st.balloons()
                else:
                    st.error("⚠️ 名前と全ての順位を入力してください。")
    else:
        st.error("🔴 現在、回答は締め切られています。管理者の開始をお待ちください。")

# --- 2. 【投影用】問題・正解表示画面 ---
elif mode == "【投影用】問題・正解表示":
    # 文字サイズを特大にし、視認性を確保
    st.markdown(f"<p style='text-align: center; font-size: 50px; color: gray; margin-bottom: 0;'>第 {conf['current_q']} 問</p>", unsafe_allow_html=True)
    st.markdown(f"<h1 style='text-align: center; font-size: 90px; margin-top: 0;'>{conf['q_text']}</h1>", unsafe_allow_html=True)
    st.divider()
    
    # 選択肢のデザイン修正（背景を濃く、文字を白く）
    st.markdown("<p style='text-align: center; font-size: 35px;'>【 選 択 肢 】</p>", unsafe_allow_html=True)
    cols = st.columns(len(options_list) if len(options_list) > 0 else 1)
    for i, opt in enumerate(options_list):
        cols[i].markdown(f"""
            <div style='text-align: center; background-color: #262730; color: white; 
            padding: 25px 10px; border-radius: 15px; font-size: 35px; font-weight: bold; 
            border: 3px solid #4B4B4B;'>{opt}</div>
        """, unsafe_allow_html=True)
    
    st.divider()

    # 正解表示（管理者が採点実行した時のみ表示）
    if conf['show_ans'] == 1:
        st.markdown("<h1 style='text-align: center; color: #ff4b4b; font-size: 110px; margin-top: 40px;'>正解発表！</h1>", unsafe_allow_html=True)
        a1, a2, a3 = st.columns(3)
        a1.metric("🏆 1位", conf['last_ans1'])
        a2.metric("🥈 2位", conf['last_ans2'])
        a3.metric("🥉 3位", conf['last_ans3'])
        st.balloons()
    else:
        st.markdown("<h2 style='text-align: center; color: #555; font-size: 45px; margin-top: 50px;'>正解発表をお楽しみに...</h2>", unsafe_allow_html=True)

    # 投影画面は5秒ごとに自動リフレッシュして管理者の操作を反映
    time.sleep(5)
    st.rerun()

# --- 3. 総合ランキング画面 ---
elif mode == "総合ランキング":
    st.title("📊 リアルタイム・スコアランキング")
    df_rank = pd.read_sql_query("SELECT name as 名前, SUM(score) as 合計点 FROM scores GROUP BY name ORDER BY 合計点 DESC, 名前 ASC", conn)
    
    if not df_rank.empty:
        # 上位15名を表示
        st.table(df_rank.head(15)) 
    else:
        st.info("集計データがありません。採点が完了するとここにランキングが表示されます。")
    
    # ランキングも10秒ごとに自動更新
    time.sleep(10)
    st.rerun()

# --- 4. 管理者画面 ---
elif mode == "管理者画面":
    st.title("⚙️ 管理者専用パネル")
    
    if not st.session_state.admin_logged_in:
        pwd = st.text_input("管理者パスワードを入力", type="password")
        if st.button("ログイン"):
            if pwd == "admin123":
                st.session_state.admin_logged_in = True
                st.rerun()
            else:
                st.error("パスワードが違います")
    else:
        if st.sidebar.button("ログアウト"):
            st.session_state.admin_logged_in = False
            st.rerun()

        # A. 進行と問題の設定
        st.subheader("📢 進行・問題文の設定")
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            new_q = st.number_input("現在の問題番号", value=int(conf['current_q']), min_value=1)
            new_q_text = st.text_input("問題文（投影画面に大きく出ます）", value=conf['q_text'])
            status = st.radio("回答受付状態", ["締め切り", "受付中"], index=1 if conf['is_open'] == 1 else 0)
            
            if st.button("進行設定を保存（投影画面を更新）"):
                # 設定保存時、新しい問題になるので正解表示フラグ(show_ans)を0にリセット
                conn.cursor().execute("UPDATE settings SET current_q=?, q_text=?, is_open=?, show_ans=0 WHERE id=1", 
                                      (new_q, new_q_text, 1 if status == "受付中" else 0))
                conn.commit()
                st.toast("設定を保存しました。投影画面が次問へ切り替わります。")
                time.sleep(0.5)
                st.rerun()

        with col_c2:
            new_opts = st.text_area("選択肢（カンマ区切りで入力）", value=conf['options'])
            if st.button("選択肢のみ更新"):
                conn.cursor().execute("UPDATE settings SET options=? WHERE id=1", (new_opts,))
                conn.commit()
                st.success("選択肢を更新しました。")

        st.divider()

        # B. 採点セクション（受付中はロック）
        st.subheader("🎯 採点と正解発表")
        if conf['is_open'] == 1:
            st.warning("⚠️ 現在「受付中」です。採点するには、上の設定を「締め切り」に変更して保存してください。")
        else:
            cur_q = int(conf['current_q'])
            df_current = pd.read_sql_query(f"SELECT name, g1, g2, g3 FROM scores WHERE q_id={cur_q}", conn)
            
            # 出題者の回答読み込み
            st.write("▼ 出題者のスマホ回答を正解としてコピーする（任意）")
            target_user = st.selectbox("回答者リストから出題者を選択", ["-- 手動で選ぶ --"] + list(df_current['name']))
            
            # セレクトボックスの初期値制御
            def_ans = ["未選択"] * 3
            if target_user != "-- 手動で選ぶ --":
                u_row = df_current[df_current['name'] == target_user].iloc[0]
                def_ans = [u_row['g1'], u_row['g2'], u_row['g3']]
                st.info(f"読み込み済み：1位({def_ans[0]}), 2位({def_ans[1]}), 3位({def_ans[2]})")

            sc1, sc2, sc3 = st.columns(3)
            ans1 = sc1.selectbox("正解1位", ["未選択"] + options_list, index=(options_list.index(def_ans[0])+1) if def_ans[0] in options_list else 0)
            ans2 = sc2.selectbox("正解2位", ["未選択"] + options_list, index=(options_list.index(def_ans[1])+1) if def_ans[1] in options_list else 0)
            ans3 = sc3.selectbox("正解3位", ["未選択"] + options_list, index=(options_list.index(def_ans[2])+1) if def_ans[2] in options_list else 0)
            
            if st.button("採点実行（投影画面に正解を表示する）"):
                if "未選択" not in [ans1, ans2, ans3]:
                    correct = [ans1, ans2, ans3]
                    # 全参加者の採点計算と更新
                    for _, row in df_current.iterrows():
                        u_guess = [row['g1'], row['g2'], row['g3']]
                        score = calculate_score(correct, u_guess)
                        conn.cursor().execute("UPDATE scores SET score=? WHERE q_id=? AND name=?", (score, cur_q, row['name']))
                    
                    # 投影画面に表示するためのフラグを1にし、正解を保存
                    conn.cursor().execute("UPDATE settings SET last_ans1=?, last_ans2=?, last_ans3=?, show_ans=1 WHERE id=1", 
                                          (ans1, ans2, ans3))
                    conn.commit()
                    st.success("✨ 第 {cur_q} 問の集計が完了しました！投影画面をご確認ください。")
                    st.balloons()
                else:
                    st.error("正解を1位から3位まで全て選択してください。")
