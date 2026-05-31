# 🧱 BlockWhisper 開發協作指南 (Internal README)

哈囉！這裡是 BlockWhisper 的核心程式碼庫。
我們目前的架構正在經歷一次重大的進化：從原本的「Merkle Tree 測試版」，正式邁向業界最高標準的「無錢包架構 (Walletless) + Google SSO + 環簽章 (Ring Signatures)」。

為了讓開發體驗更順暢，我們已經導入了自動化建置與部署腳本。請在開發或測試前，先詳細閱讀以下說明。

---

## 📂 資料夾結構說明

專案主要分為兩個獨立的環境（區塊鏈與 Python 後端）：
```text
📦 BlockWhisper_Project
 ┣ 📂 blockchain/        # 智能合約與 Hardhat 開發環境
 ┃ ┣ 📂 contracts/       # Solidity 原始碼 (CampusWall.sol)
 ┃ ┣ 📂 artifacts/       # 📌 編譯後產生的 ABI 與 Bytecode (系統自動產生)
 ┃ ┗ 📜 hardhat.config.ts# Hardhat 設定檔
 ┃
 ┣ 📂 python_app/        # 後端 API 與前端網頁
 ┃ ┣ 📜 api.py           # FastAPI 伺服器 (未來的代付中心 Relayer)
 ┃ ┣ 📜 app.py           # Streamlit 前端介面
 ┃ ┣ 📜 deploy.py        # 🤖 自動部署智能合約腳本
 ┃ ┗ 📜 requirements.txt # Python 套件清單
 ┃
 ┣ 📜 setup.bat          # 🛠️ [Windows] 一鍵安裝開發環境腳本
 ┣ 📜 start.bat          # 🚀 [Windows] 一鍵啟動全端系統腳本
 ┣ 📜 setup.sh           # 🛠️ [Mac/Linux] 一鍵安裝開發環境腳本
 ┗ 📜 start.sh           # 🚀 [Mac/Linux] 一鍵啟動全端系統腳本
 ```

---

# 🚀 本地端開發環境啟動流程 (自動化版)
第一步：環境初始化 (僅首次 Clone 或套件更新時需要)
確保電腦已安裝 Node.js 與 Python 3。

Windows

在專案根目錄下，對著 setup.bat 點擊兩下執行。
Mac/Linux
```
chmod +x setup.sh
./setup.sh
```

腳本會自動建立虛擬環境 (venv)、安裝 Python 套件、並下載 Hardhat 區塊鏈相依套件。

看到「所有環境建置完畢！」後，按任意鍵關閉視窗。

第二步：一鍵啟動系統

Windows:

在專案根目錄下，對著 start.bat 點擊兩下執行。

Mac/Linux
```
chmod +x start.sh
./start.sh
```

腳本會自動幫你：

啟動本地 Hardhat 區塊鏈節點 (http://127.0.0.1:8545)

自動編譯 CampusWall.sol 智能合約

執行 deploy.py 自動將合約部署上鏈，並把新地址寫入 app.py

啟動 FastAPI 後端伺服器 (http://127.0.0.1:8000)

啟動 Streamlit 網頁介面

系統會彈出三個黑色終端機視窗，請勿關閉。 若要停止系統，直接將那三個視窗打叉關閉即可。

---
# 開發里程碑與時程規劃
🚩 Milestone 1：Google SSO 與本地短暫金鑰生成
目標：讓學生能用北大信箱登入，且網頁能在背景自動孵化出一對全新的匿名金鑰。

Task 1.1：在 GCP 申請 OAuth 2.0 憑證，並在 Streamlit 前端實作 Google 登入按鈕，取得 id_token。

Task 1.2：完全捨棄 MetaMask。在前端登入後，使用 Python 內建套件 (os.urandom 與 ecdsa) 在背景隨機生成「環簽章私鑰/公鑰」，並存入 st.session_state 中（關閉網頁即銷毀）。

Task 1.3：FastAPI 建立 /auth/register API，驗證 Google Token 中的信箱必須為 @gm.ntpu.edu.tw。

🚩 Milestone 2：化身代付中心 (Relayer) 與公鑰註冊
目標：讓 FastAPI 後端拿著測試幣，幫通過驗證的學生把公鑰寫入區塊鏈。

Task 2.1：在 FastAPI 設定官方錢包（使用 Hardhat 第一組私鑰），連線至本地節點。

Task 2.2：擴充 /auth/register API，驗證信箱成功後，FastAPI 代付 Gas Fee，呼叫智能合約將該學生的「環簽公鑰」寫入鏈上白名單。

Task 2.3：在後端實作 Rate Limiting（例如同一個信箱每 5 分鐘只能註冊一把公鑰），作為無錢包架構下的防洗版配套。

🚩 Milestone 3：環簽章運算與代付發文 (核心難關)
目標：在本地端完成環簽章數學運算，並讓伺服器代為發布留言。

Task 3.1：尋找並整合支援 secp256k1 曲線的開源「Python 環簽章腳本」與「Solidity 驗證合約」。

Task 3.2：發文時，前端向鏈上抓取 10 把誘餌公鑰，加上自己的公鑰，使用本地私鑰對留言進行 LSAG 環簽章運算，產出 (Signature, Key Image)。

Task 3.3：建立 FastAPI /post API。前端不直接對接區塊鏈，而是把算好的環簽章資料丟給 FastAPI，由 FastAPI 代付手續費執行 postMessage 永久上鏈。

🚩 Milestone 4：全線貫通與安全銷毀
目標：串接所有流程，確保閱後即焚的零知識安全性。

Task 4.1：跑通完整流程（登入 -> 背景生金鑰 -> 後端註冊 -> 前端算環簽 -> 後端代發 -> 網頁更新）。

Task 4.2：落實前端資安，確保發文成功後立刻執行 del st.session_state['private_key']，徹底清除記憶體中的私鑰痕跡。
✅ 目前已完成功能 (Milestones)
環境建置：完成 Hardhat 本地節點架構與開發環境配置。

智能合約開發：部署 CampusWall.sol，實作了公鑰註冊、環簽章發文與 Event 事件廣播。

Web2.5 身份認證：串接 Google OAuth 登入，並實作後端自動將學生公鑰「代付上鏈 (Relayer)」。

匿名發文系統：完成前端留言板功能，支援匿名貼文提交與鏈上數據廣播。

即時動態牆：成功從區塊鏈讀取歷史貼文並即時呈現在前端介面上。
### 🚀 如何啟動專案
1. **啟動區塊鏈節點**：
   `cd blockchain && npx hardhat node` (請保持終端機開啟)
2. **啟動後端伺服器**：
   `cd python_app && uvicorn api:app --reload`
3. **啟動前端網頁**：
   `streamlit run app.py`