import os
import ecdsa
import streamlit as st
import requests
import hashlib
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

    # ================= 1. 發布新貼文 (主文) =================
    with st.container(border=True):
        st.subheader("✍️ 發表新貼文")
        message = st.text_area("想說點什麼？", placeholder="發布一篇新的靠北文...")
        
        # 🌟 新增：圖片上傳元件
        uploaded_file = st.file_uploader("📎 附上梗圖或照片 (選填)", type=["jpg", "png", "jpeg", "gif"])
        
        if st.button("發布貼文 🚀", use_container_width=True):
            # 檢查是否全空
            if not message and not uploaded_file:
                st.error("⚠️ 留言與圖片不能同時為空喔！")
            else:
                with st.spinner("正在處理資料與上鏈... (若有圖片需較長時間)"):
                    try:
                        import hashlib
                        
                        final_message = message
                        
                        # 🌟 新增邏輯：如果有傳圖片，先打 API 上傳到 IPFS
                        if uploaded_file:
                            st.toast("正在將圖片上傳至 IPFS 星際檔案系統...")
                            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                            img_res = requests.post("http://127.0.0.1:8000/upload_image", files=files)
                            
                            if img_res.status_code == 200:
                                ipfs_url = img_res.json()["ipfs_url"]
                                # ✨ 神技：巧妙利用 Markdown 語法，把圖片嵌入到留言文字中
                                final_message += f"\n\n![image]({ipfs_url})"
                            else:
                                st.error("❌ 圖片上傳 IPFS 失敗！")
                                st.stop()

                        # 接下來的發文邏輯跟原本一模一樣，只是使用組合好的 final_message
                        sk_bytes = bytes.fromhex(st.session_state.ephemeral_private_key)
                        msg_bytes = final_message.encode('utf-8')
                        parent_id_bytes = str(0).encode('utf-8')
                        key_image = hashlib.sha256(sk_bytes + msg_bytes + parent_id_bytes).hexdigest()
                        
                        res = requests.post(
                            "http://127.0.0.1:8000/wall/post",
                            json={
                                "message": final_message,
                                "parent_id": 0,
                                "key_image": key_image
                            }
                        )
                        
                        if res.status_code == 200:
                            tx_hash = res.json()["tx_hash"]
                            st.success(f"✅ 發文成功！您的匿名心聲已永久刻在區塊鏈上。")
                            st.info(f"🔗 TxHash: {tx_hash}")
                            st.balloons()
                            st.rerun() # 自動重整看新貼文
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

    # ================= 2. 抓取鏈上留言並進行渲染 =================
    try:
        res = requests.get("http://127.0.0.1:8000/wall/posts")
        if res.status_code == 200:
            posts = res.json().get("posts", [])
            
            if not posts:
                st.info("📭 目前牆上空空如也，趕快去搶頭香吧！")
            else:
                # 【新增邏輯】：將抓回來的貼文區分為「主貼文」與「回覆」
                main_posts = [p for p in posts if p['parent_id'] == 0]
                
                replies_dict = {}
                for p in posts:
                    if p['parent_id'] != 0:
                        if p['parent_id'] not in replies_dict:
                            replies_dict[p['parent_id']] = []
                        # 因為後端回傳是最新的在最上面，這裡用 insert 讓同篇貼文的舊回覆排在上面，符合閱讀習慣
                        replies_dict[p['parent_id']].insert(0, p)

                # 渲染主貼文
                for post in main_posts:
                    with st.container(border=True):
                        # 顯示主貼文內容
                        with st.chat_message("user", avatar="🕵️‍♂️"):
                            st.markdown(f"### {post['message']}")
                            st.caption(f"Post ID: #{post['post_id']} | 🔗 TxHash: {post['tx_hash'][:12]}...{post['tx_hash'][-4:]}")
                        
                        # 顯示這篇貼文的專屬回覆
                        post_replies = replies_dict.get(post['post_id'], [])
                        if post_replies:
                            st.markdown("---")
                            for reply in post_replies:
                                with st.chat_message("user", avatar="💬"):
                                    st.markdown(f"{reply['message']}")
                                    st.caption(f"Reply ID: #{reply['post_id']} | 🔗 TxHash: {reply['tx_hash'][:12]}...{reply['tx_hash'][-4:]}")

                        # 撰寫回覆的 UI (使用 expander 收納，避免畫面過於冗長)
                        with st.expander(f"✏️ 回覆此貼文 (#{post['post_id']})"):
                            # 注意：Streamlit 的表單元件必須要有 unique key，這裡用 post_id 組合
                            reply_msg = st.text_input("輸入回覆內容", key=f"input_{post['post_id']}")
                            if st.button("送出回覆", key=f"btn_{post['post_id']}"):
                                if not reply_msg:
                                    st.error("⚠️ 回覆不能為空喔！")
                                else:
                                    with st.spinner("正在請 Relayer 代付回覆上鏈..."):
                                        try:
                                            sk_bytes = bytes.fromhex(st.session_state.ephemeral_private_key)
                                            msg_bytes = reply_msg.encode('utf-8')
                                            
                                            # 【關鍵防護】：把 parent_id 也加入 Key Image 雜湊
                                            parent_id_bytes = str(post['post_id']).encode('utf-8')
                                            key_image = hashlib.sha256(sk_bytes + msg_bytes + parent_id_bytes).hexdigest()
                                            
                                            res = requests.post(
                                                "http://127.0.0.1:8000/wall/post",
                                                json={
                                                    "message": reply_msg,
                                                    "parent_id": post['post_id'], # 綁定主貼文的 ID
                                                    "key_image": key_image
                                                }
                                            )
                                            
                                            if res.status_code == 200:
                                                st.success("✅ 回覆成功！")
                                                st.rerun() # 重新載入畫面以顯示新回覆
                                            else:
                                                st.error(f"❌ 回覆失敗：{res.json().get('detail')}")
                                        except Exception as e:
                                            st.error(f"無法連線到伺服器：{e}")
        else:
            st.error("無法載入貼文，請確認區塊鏈節點是否正常運作。")
    except Exception as e:
        st.error(f"連線後端失敗：{e}")