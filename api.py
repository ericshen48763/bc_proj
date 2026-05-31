import os
import time
import requests
from dotenv import load_dotenv  # 新增這一行
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from web3 import Web3

# 載入 .env 環境變數
load_dotenv()

app = FastAPI(title="BlockWhisper Relayer Hub")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)

# ================= ⚠️ 1. 從環境變數讀取 GCP 金鑰 =================
# 使用 os.getenv 安全抓取，不再讓字串裸奔
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = "http://localhost:8501/"

# ================= ⚠️ 2. 從環境變數讀取合約資訊 =================
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")

# 加上一個安全防護網，確保啟動前變數都有抓到
if not all([GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, CONTRACT_ADDRESS]):
    raise ValueError("⚠️ 啟動失敗：缺少必要的環境變數！請確認 .env 檔案已設定。")
CONTRACT_ABI =[
	{
		"inputs": [],
		"stateMutability": "nonpayable",
		"type": "constructor"
	},
	{
		"anonymous": False,
		"inputs": [
			{
				"indexed": True,
				"internalType": "uint256",
				"name": "postId",
				"type": "uint256"
			},
			{
				"indexed": True,
				"internalType": "uint256",
				"name": "parentId",
				"type": "uint256"
			},
			{
				"indexed": False,
				"internalType": "string",
				"name": "message",
				"type": "string"
			}
		],
		"name": "ConfessionPosted",
		"type": "event"
	},
	{
		"inputs": [
			{
				"internalType": "string",
				"name": "message",
				"type": "string"
			},
			{
				"internalType": "uint256",
				"name": "parentId",
				"type": "uint256"
			},
			{
				"internalType": "bytes32",
				"name": "keyImage",
				"type": "bytes32"
			}
		],
		"name": "postMessageWithRing",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"anonymous": False,
		"inputs": [
			{
				"indexed": True,
				"internalType": "bytes32",
				"name": "pubKey",
				"type": "bytes32"
			}
		],
		"name": "PublicKeyRegistered",
		"type": "event"
	},
	{
		"inputs": [
			{
				"internalType": "bytes32",
				"name": "pubKey",
				"type": "bytes32"
			}
		],
		"name": "registerPublicKey",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [],
		"name": "getRingPublicKeys",
		"outputs": [
			{
				"internalType": "bytes32[]",
				"name": "",
				"type": "bytes32[]"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [],
		"name": "nextPostId",
		"outputs": [
			{
				"internalType": "uint256",
				"name": "",
				"type": "uint256"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [],
		"name": "owner",
		"outputs": [
			{
				"internalType": "address",
				"name": "",
				"type": "address"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "uint256",
				"name": "",
				"type": "uint256"
			}
		],
		"name": "ringPublicKeys",
		"outputs": [
			{
				"internalType": "bytes32",
				"name": "",
				"type": "bytes32"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "bytes32",
				"name": "",
				"type": "bytes32"
			}
		],
		"name": "usedKeyImages",
		"outputs": [
			{
				"internalType": "bool",
				"name": "",
				"type": "bool"
			}
		],
		"stateMutability": "view",
		"type": "function"
	}
]

# ================= Task 2.1：設定官方代付錢包 (Relayer) =================
RPC_URL = "http://127.0.0.1:8545"
w3 = Web3(Web3.HTTPProvider(RPC_URL))

# 私鑰也必須從環境變數讀取
RELAYER_PRIVATE_KEY = os.getenv("RELAYER_PRIVATE_KEY")
if not RELAYER_PRIVATE_KEY:
    raise ValueError("⚠️ 啟動失敗：缺少 RELAYER_PRIVATE_KEY 環境變數。")

relayer_account = w3.eth.account.from_key(RELAYER_PRIVATE_KEY)
contract = w3.eth.contract(address=w3.to_checksum_address(CONTRACT_ADDRESS), abi=CONTRACT_ABI)

# Task 2.3：簡易記憶體限流 (紀錄 Email -> 上次註冊時間戳)
rate_limit_db = {}

class RegisterRequest(BaseModel):
    code: str
    public_key: str

@app.post("/auth/register")
def register_user(req: RegisterRequest):
    token_url = "https://oauth2.googleapis.com/token"
    payload = {"code": req.code, "client_id": GOOGLE_CLIENT_ID, "client_secret": GOOGLE_CLIENT_SECRET, "redirect_uri": REDIRECT_URI, "grant_type": "authorization_code"}
    
    try:
        # 1. Google 驗證
        token_res = requests.post(token_url, data=payload).json()
        idinfo = id_token.verify_oauth2_token(token_res["id_token"], google_requests.Request(), GOOGLE_CLIENT_ID)
        email = idinfo.get("email", "")
        
        if not email or not email.endswith("@gm.ntpu.edu.tw"):
            raise HTTPException(status_code=403, detail="僅限台北大學 @gm.ntpu.edu.tw 信箱註冊。")
        
        # 2. Task 2.3：限流防洗版檢查 (5分鐘內只能註冊一次)
        current_time = time.time()
        if email in rate_limit_db and (current_time - rate_limit_db[email] < 300):
            remaining = int(300 - (current_time - rate_limit_db[email]))
            raise HTTPException(status_code=429, detail=f"註冊過於頻繁，請等待 {remaining} 秒。")
        rate_limit_db[email] = current_time
        
        # 3. Task 2.2：由 Relayer 代付 Gas，幫學生的公鑰上鏈！
        try:
            # 轉換公鑰格式為合約相容的 bytes32
            pubkey_bytes = bytes.fromhex(req.public_key.replace("0x", ""))
            padded_pubkey = pubkey_bytes.ljust(32, b'\x00')[:32]
            
            # Relayer 建立交易並代付手續費
            nonce = w3.eth.get_transaction_count(relayer_account.address)
            tx = contract.functions.registerPublicKey(padded_pubkey).build_transaction({
                'from': relayer_account.address,
                'nonce': nonce,
                'gas': 200000,
                'gasPrice': w3.eth.gas_price
            })
            signed_tx = w3.eth.account.sign_transaction(tx, private_key=RELAYER_PRIVATE_KEY)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            w3.eth.wait_for_transaction_receipt(tx_hash)
            print(f"✅ 公鑰上鏈成功！TxHash: {tx_hash.hex()}")
        except Exception as e:
            print(f"⚠️ 公鑰上鏈失敗: {e}")
            raise HTTPException(status_code=500, detail="智能合約互動失敗，請檢查節點與合約設定。")
            
        return {
            "status": "success",
            "student_id": email.split("@")[0],
            "registered_public_key": req.public_key
        }
        
    except ValueError:
        raise HTTPException(status_code=401, detail="Google Token 無效或已過期")
    
# ================= Task 3：匿名發文與抓取公鑰 =================
class PostRequest(BaseModel):
    message: str
    parent_id: int
    key_image: str
    # (實務上這裡會傳入完整的環簽章，這裡以模擬防偽造 Key Image 為例)

@app.post("/wall/post")
def post_to_wall(req: PostRequest):
    try:
        # 1. 轉換 Key Image 格式以符合智能合約的 bytes32
        key_image_bytes = bytes.fromhex(req.key_image.replace("0x", ""))
        padded_key_image = key_image_bytes.ljust(32, b'\x00')[:32]
        
        # 2. Relayer 代付上鏈 (呼叫合約的 postMessageWithRing)
        nonce = w3.eth.get_transaction_count(relayer_account.address)
        tx = contract.functions.postMessageWithRing(
            req.message, 
            req.parent_id, 
            padded_key_image
        ).build_transaction({
            'from': relayer_account.address,
            'nonce': nonce,
            'gas': 300000,  # 發文需要的 Gas 比較多一點
            'gasPrice': w3.eth.gas_price
        })
        
        signed_tx = w3.eth.account.sign_transaction(tx, private_key=RELAYER_PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        w3.eth.wait_for_transaction_receipt(tx_hash)
        
        print(f"✅ 匿名貼文上鏈成功！TxHash: {tx_hash.hex()}")
        return {"status": "success", "tx_hash": tx_hash.hex()}
        
    except Exception as e:
        print(f"⚠️ 發文失敗: {e}")
        raise HTTPException(status_code=500, detail=f"上鏈失敗: {str(e)}")

@app.get("/wall/keys")
def get_public_keys():
    """前端用來抓取鏈上所有公鑰（當作環簽章的誘餌名單）"""
    try:
        keys = contract.functions.getRingPublicKeys().call()
        return {"keys": [w3.to_hex(k) for k in keys]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/wall/posts")
def get_all_posts():
    """抓取區塊鏈上所有的 ConfessionPosted 事件"""
    try:
        # 修正：將 fromBlock 改為 from_block
        logs = contract.events.ConfessionPosted.get_logs(from_block=0)
        posts = []
        for log in logs:
            posts.append({
                "post_id": log.args.postId,
                "parent_id": log.args.parentId,
                "message": log.args.message,
                "tx_hash": log.transactionHash.hex()
            })
        
        # 將陣列反轉，讓最新的留言顯示在最上面
        return {"status": "success", "posts": posts[::-1]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"讀取貼文失敗: {str(e)}")