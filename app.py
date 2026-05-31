import os
import ecdsa
import streamlit as st
import requests
from dotenv import load_dotenv  # 新增這一行

# 載入 .env 環境變數
load_dotenv()
# ================= Task 1.2：背景生成環簽章金鑰 =================
def generate_ephemeral_keys():
    """完全捨棄 MetaMask，在本地生成一次性 SECP256k1 金鑰對"""
    private_key = ecdsa.SigningKey.generate(curve=ecdsa.SECP256k1)
    public_key = private_key.get_verifying_key()
    return private_key.to_string().hex(), public_key.to_string().hex()

# 初始化 Session State
if "ephemeral_private_key" not in st.session_state:
    st.session_state.ephemeral_private_key = None
if "ephemeral_public_key" not in st.session_state:
    st.session_state.ephemeral_public_key = None
if "student_id" not in st.session_state:
    st.session_state.student_id = None

# ================= 介面設計 =================
st.set_page_config(page_title="BlockWhisper", page_icon="🧱", layout="centered")

with st.sidebar:
    st.title("🧱 BlockWhisper")
    st.markdown("去中心化校園匿名牆 (無錢包架構版)")
    st.divider()
    page = st.radio("請選擇操作介面：", ["🔑 身分驗證", "📜 留言板"])
    st.divider()
    # 🚨 Task 1.2：這裡已經把原本的 MetaMask 下拉選單徹底刪除了！
    if st.session_state.ephemeral_public_key:
        st.caption("🔒 您的拋棄式公鑰:")
        st.code(f"0x{st.session_state.ephemeral_public_key[:12]}...")

if page == "🔑 身分驗證":
    st.header("🔑 學生身分驗證與金鑰孵化")
    st.markdown("系統已全面升級！請使用您的 **北大 Google 信箱** 進行登入驗證。")
    
    # ⚠️ 從環境變數讀取 Client ID
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    REDIRECT_URI = "http://localhost:8501/"
    
    if not GOOGLE_CLIENT_ID:
        st.error("⚠️ 系統錯誤：找不到 GOOGLE_CLIENT_ID 環境變數。")
        st.stop()
        
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"response_type=code&"
        f"client_id={GOOGLE_CLIENT_ID}&"
        f"redirect_uri={REDIRECT_URI}&"
        f"scope=openid%20email%20profile"
    )
    
    query_params = st.query_params
    if "code" in query_params:
        auth_code = query_params["code"]
        
        with st.spinner("正在安全孵化匿名金鑰並向後端驗證身分..."):
            try:
                # 1. 前端背景隨機生成「環簽章私鑰/公鑰」
                if not st.session_state.ephemeral_private_key:
                    sk, pk = generate_ephemeral_keys()
                    st.session_state.ephemeral_private_key = sk
                    st.session_state.ephemeral_public_key = pk
                
                # 2. 將 code 與公鑰送往 FastAPI
                res = requests.post(
                    "http://127.0.0.1:8000/auth/register", 
                    json={
                        "code": auth_code,
                        "public_key": st.session_state.ephemeral_public_key
                    }
                )
                
                if res.status_code == 200:
                    st.session_state.student_id = res.json()["student_id"]
                    st.success(f"✅ 驗證成功！歡迎同學 ({st.session_state.student_id})")
                    st.balloons()
                    st.query_params.clear() # 清空網址列的 code
                else:
                    st.error(f"❌ 登入失敗：{res.json().get('detail')}")
                    if st.button("重新登入"):
                        st.query_params.clear()
                        st.rerun()
            except Exception as e:
                st.error(f"無法連線到伺服器：{e}")
                
    else:
        if st.session_state.student_id:
            st.success(f"🎉 狀態：已登入並生成專屬金鑰 (學號: {st.session_state.student_id})")
            if st.button("登出並銷毀金鑰", type="secondary"):
                st.session_state.ephemeral_private_key = None
                st.session_state.ephemeral_public_key = None
                st.session_state.student_id = None
                st.rerun()
        else:
            st.info("💡 提示：非 @gm.ntpu.edu.tw 網域的帳號將會被後端伺服器拒絕。")
            st.link_button("🌐 使用 Google 帳號登入", auth_url, type="primary", use_container_width=True)

elif page == "📜 留言板":
    st.header("📜 校園匿名留言板")
    
    if not st.session_state.student_id:
        st.warning("🔒 存取被拒絕：您尚未登入！")
        st.info("👉 請點擊左側欄選單回到「🔑 身分驗證」登入後即可解鎖。")
        st.stop()

    with st.container(border=True):
        st.subheader("✍️ 發表新貼文")
        message = st.text_area("想說點什麼？", placeholder="發布一篇新的靠北文...")
        
        if st.button("發布貼文 🚀", use_container_width=True):
            if not message:
                st.error("⚠️ 留言不能為空喔！")
            else:
                with st.spinner("正在抓取鏈上公鑰、生成環簽章並請 Relayer 代付上鏈..."):
                    try:
                        # 1. 生成專屬的 Key Image (避免同一句話重複發送，也作為唯一識別)
                        import hashlib
                        sk_bytes = bytes.fromhex(st.session_state.ephemeral_private_key)
                        msg_bytes = message.encode('utf-8')
                        key_image = hashlib.sha256(sk_bytes + msg_bytes).hexdigest()
                        
                        # 2. 將貼文與 Key Image 送交後端 Relayer
                        res = requests.post(
                            "http://127.0.0.1:8000/wall/post",
                            json={
                                "message": message,
                                "parent_id": 0,
                                "key_image": key_image
                            }
                        )
                        
                        if res.status_code == 200:
                            tx_hash = res.json()["tx_hash"]
                            st.success(f"✅ 發文成功！您的匿名心聲已永久刻在區塊鏈上。")
                            st.info(f"🔗 交易紀錄 (TxHash): {tx_hash}")
                            st.balloons()
                        else:
                            st.error(f"❌ 發文失敗：{res.json().get('detail')}")
                    except Exception as e:
                        st.error(f"無法連線到伺服器：{e}")

    st.divider()
    
    col1, col2 = st.columns([4, 1])
    with col1:
        st.subheader("最新動態 📡")
    with col2:
        if st.button("🔄 重新整理", use_container_width=True):
            st.rerun()

    # 呼叫後端 API 抓取鏈上留言
    try:
        res = requests.get("http://127.0.0.1:8000/wall/posts")
        if res.status_code == 200:
            posts = res.json().get("posts", [])
            
            if not posts:
                st.info("📭 目前牆上空空如也，趕快去搶頭香吧！")
            else:
                for post in posts:
                    with st.chat_message("user", avatar="🕵️‍♂️"):
                        st.markdown(f"### {post['message']}")
                        st.caption(f"Post ID: #{post['post_id']} | 🔗 TxHash: {post['tx_hash'][:12]}...{post['tx_hash'][-4:]}")
        else:
            st.error("無法載入貼文，請確認區塊鏈節點是否正常運作。")
    except Exception as e:
        st.error(f"連線後端失敗：{e}")