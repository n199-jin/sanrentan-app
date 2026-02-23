import streamlit as st
import sqlite3
import pandas as pd

# --- データベース設定 ---
def init_db():
    conn = sqlite3.connect('sanrentan_v3.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS answers 
                 (name TEXT PRIMARY KEY, rank1 TEXT, rank2 TEXT, rank3 TEXT, score INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS settings 
                 (id INTEGER PRIMARY KEY, options TEXT, ans1 TEXT, ans2 TEXT, ans3 TEXT)''')
    c.execute("INSERT OR IGNORE INTO settings (id, options) VALUES (1, 'A,B,C,D')")
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

# --- アプリ設定 ---
st.set_page_config(page_title="サンレンタン大会", layout="wide")

# 最新の設定を取得
def get_settings():
    return pd.read_sql_query("SELECT * FROM settings WHERE id=1", conn).iloc[0]

settings = get_settings()
options_list = [opt.strip() for opt in settings['options'].split(',') if opt.strip()]

# --- サイドバー：画面切り替え ---
st.sidebar.title("メニュー")
mode = st.sidebar.radio("表示モード切替", ["参加者画面（投票）", "ランキング閲覧", "管理者画面"])

# --- 1. 参加者画面 ---
if mode == "参加者画面（投票）":
    st.title("📝 予想を投票する")
    if not options_list:
        st.warning("管理者が選択肢を設定するまでお待ちください。")
    else:
        with st.form("vote_form"):
            name = st.text_input("あなたの名前（必須）", placeholder="例：田中太郎")
            st.info(f"【選択肢】 {', '.join(options_list)}")
            c1, c2, c3 = st.columns(3)
            g1 = c1.selectbox("1位予想", ["未選択"] + options_list, key="g1")
            g2 = c2.selectbox("2位予想", ["未選択"] + options_list, key="g2")
            g3 = c3.selectbox("3位予想", ["未選択"] + options_list, key="g3")
            
            if st.form_submit_button("予想を送信"):
                if name and g1 != "未選択" and g2 != "未選択" and g3 != "未選択":
                    if len({g1, g2, g3}) < 3:
                        st.error("同じ選択肢は選べません！")
                    else:
                        c = conn.cursor()
                        c.execute("INSERT OR REPLACE INTO answers (name, rank1, rank2, rank3, score) VALUES (?, ?, ?, ?, 0)", 
                                  (name, g1, g2, g3))
                        conn.commit()
                        st.success(f"{name}さんの予想を受け付けました！")
                else:
                    st.error("名前と3つの順位をすべて正しく選択してください。")

# --- 2. ランキング閲覧画面 ---
elif mode == "ランキング閲覧":
    st.title("📊 現在のランキング")
    df_ranking = pd.read_sql_query("SELECT name, score, rank1, rank2, rank3 FROM answers ORDER BY score DESC, name ASC", conn)
    if not df_ranking.empty:
        st.dataframe(df_ranking, use_container_width=True)
    else:
        st.info("まだ回答がありません。")

# --- 3. 管理者画面 ---
elif mode == "管理者画面":
    st.title("⚙️ 管理者専用メニュー")
    password = st.sidebar.text_input("管理者パスワードを入力", type="password")
    
    # パスワードを「admin123」に設定（好きな文字に変えてください）
    if password == "admin123":
        st.success("認証されました。")
        
        # 選択肢設定
        with st.expander("1. お題（選択肢）の設定", expanded=True):
            new_options = st.text_area("選択肢をカンマ(,)区切りで入力", value=settings['options'])
            if st.button("選択肢を更新"):
                conn.cursor().execute("UPDATE settings SET options = ? WHERE id = 1", (new_options,))
                conn.commit()
                st.success("反映されました。参加者の選択肢が切り替わります。")
                st.rerun()

        # 正解入力
        with st.expander("2. 正解発表とスコア計算"):
            sc1, sc2, sc3 = st.columns(3)
            ans1 = sc1.selectbox("正解1位", ["未選択"] + options_list)
            ans2 = sc2.selectbox("正解2位", ["未選択"] + options_list)
            ans3 = sc3.selectbox("正解3位", ["未選択"] + options_list)
            
            if st.button("一括計算実行"):
                if ans1 != "未選択" and ans2 != "未選択" and ans3 != "未選択":
                    correct_ans = [ans1, ans2, ans3]
                    df_all = pd.read_sql_query("SELECT * FROM answers", conn)
                    for _, row in df_all.iterrows():
                        u_guess = [row['rank1'], row['rank2'], row['rank3']]
                        score = calculate_score(correct_ans, u_guess)
                        conn.cursor().execute("UPDATE answers SET score = ? WHERE name = ?", (score, row['name']))
                    conn.commit()
                    st.success("計算完了！ランキング画面を確認してください。")
                else:
                    st.error("正解をすべて選んでください。")

        # リセット
        if st.button("全回答データを削除（次の問題へ）"):
            conn.cursor().execute("DELETE FROM answers")
            conn.commit()
            st.warning("データをリセットしました。")
            st.rerun()
    else:
        st.error("パスワードが正しくありません。")
