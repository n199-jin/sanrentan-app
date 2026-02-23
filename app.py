import streamlit as st
import sqlite3
import pandas as pd
import time

# --- データベース設定 ---
def init_db():
    conn = sqlite3.connect('sanrentan_v7.db', check_same_thread=False)
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

def get_settings():
    # 常に最新のDB状態を取得するため、キャッシュせずに読み込む
    return pd.read_sql_query("SELECT * FROM settings WHERE id=1", conn).iloc[0]

# --- UI設定 ---
st.set_page_config(page_title="サンレンタン・フルシステム", layout="wide")

# セッション状態でログイン管理
if 'admin_logged_in' not in st.session_state:
    st.session_state.admin_logged_in = False

st.sidebar.title("🎮 メニュー")
mode = st.sidebar.radio("モード切替", ["参加者画面", "総合ランキング", "管理者画面"])

# 最新設定のロード
conf = get_settings()
options_list = [opt.strip() for opt in conf['options'].split(',') if opt.strip()]

# --- 1. 参加者画面（自動更新あり） ---
if mode == "参加者画面":
    st.title(f"📝 第 {conf['current_q']} 問：予想投票")
    
    # 状態を表示するバッジ風の表示
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
        
        btn = st.form_submit_button("予想を送信")
        if btn:
            if conf['is_open'] == 0:
                st.error("送信に失敗しました。すでに締め切られています。")
            elif name and g1 != "未選択" and g2 != "未選択" and g3 != "未選択":
                if len({g1, g2, g3}) < 3:
                    st.error("❌ 同じ選択肢は選べません！")
                else:
                    c = conn.cursor()
                    c.execute("INSERT OR IGNORE INTO users (name) VALUES (?)", (name,))
                    c.execute("INSERT OR REPLACE INTO scores (q_id, name, g1, g2, g3, score) VALUES (?, ?, ?, ?, ?, 0)", 
                              (int(conf['current_q']), name, g1, g2, g3))
                    conn.commit()
                    st.success(f"✅ 第{conf['current_q']}問を受理しました！")
                    st.balloons()
            else:
                st.error("⚠️ 未入力の項目があります。")

    # --- 自動更新ロジック ---
    # 参加者が入力中にリフレッシュされると困るため、フォーム外でカウント
    st.caption("※5秒ごとに自動更新中（管理者の操作が自動反映されます）")
    time.sleep(5)
    st.rerun()

# --- 2. 総合ランキング画面 ---
elif mode == "総合ランキング":
    st.title("📊 総合スコアランキング")
    df_rank = pd.read_sql_query("SELECT name as 名前, SUM(score) as 合計点 FROM scores GROUP BY name ORDER BY 合計点 DESC, 名前 ASC", conn)
    if not df_rank.empty:
        st.table(df_rank.head(15)) 
        with st.expander("🔍 詳細データ表示"):
            df_all = pd.read_sql_query("SELECT q_id as 問, name as 名前, score as 点数 FROM scores ORDER BY q_id DESC", conn)
            st.dataframe(df_all, use_container_width=True)
    else:
        st.info("まだ集計データがありません。")
    
    # ランキング画面も10秒ごとに更新
    time.sleep(10)
    st.rerun()

# --- 3. 管理者画面 ---
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

        # 進行管理
        st.subheader("📢 進行管理")
        col1, col2 = st.columns(2)
        with col1:
            new_q = st.number_input("現在の問題番号", value=int(conf['current_q']), min_value=1)
            status = st.radio("回答受付状態", ["締め切り", "受付中"], index=1 if conf['is_open'] == 1 else 0)
            if st.button("設定を保存・更新"):
                conn.cursor().execute("UPDATE settings SET current_q = ?, is_open = ? WHERE id = 1", 
                                      (new_q, 1 if status == "受付中" else 0))
                conn.commit()
                st.toast("設定を保存しました")
                time.sleep(0.5)
                st.rerun()

        with col2:
            new_opts = st.text_area("選択肢の編集（カンマ区切り）", value=conf['options'])
            if st.button("選択肢を反映"):
                conn.cursor().execute("UPDATE settings SET options = ? WHERE id = 1", (new_opts,))
                conn.commit()
                st.success("選択肢を更新しました。")

        st.divider()

        # 採点
        st.subheader("🎯 採点と集計")
        if conf['is_open'] == 1:
            st.error("🚨 「受付中」のため採点できません。「締め切り」にして保存してください。")
        else:
            st.write(f"第 {conf['current_q']} 問の正解を入力")
            sc1, sc2, sc3 = st.columns(3)
            ans1 = sc1.selectbox("正解1位", ["未選択"] + options_list)
            ans2 = sc2.selectbox("正解2位", ["未選択"] + options_list)
            ans3 = sc3.selectbox("正解3位", ["未選択"] + options_list)
            
            if st.button("この問題の採点を実行"):
                if "未選択" not in [ans1, ans2, ans3]:
                    with st.spinner('集計中...'):
                        correct = [ans1, ans2, ans3]
                        cur_q = int(conf['current_q'])
                        # 現在の問題の回答を抽出
                        df_target = pd.read_sql_query(f"SELECT * FROM scores WHERE q_id={cur_q}", conn)
                        for _, row in df_target.iterrows():
                            u_guess = [row['g1'], row['g2'], row['g3']]
                            sc = calculate_score(correct, u_guess)
                            conn.cursor().execute("UPDATE scores SET score=? WHERE q_id=? AND name=?", (sc, cur_q, row['name']))
                        conn.commit()
                    st.success(f"✨ 第 {cur_q} 問の集計完了！")
                    st.balloons()
                else:
                    st.error("正解をすべて選択してください。")
