import json
import re
from web3 import Web3

# 1. 連線到本地 Hardhat 節點
w3 = Web3(Web3.HTTPProvider('http://127.0.0.1:8545'))
if not w3.is_connected():
    print("❌ 無法連線到 Hardhat 節點，請確認節點已啟動")
    exit()

# 2. 設定部署帳號 (拿第一組測試帳號)
deployer_account = w3.eth.accounts[0]
w3.eth.default_account = deployer_account
print(f"使用帳號部署: {deployer_account}")

# 3. 讀取編譯好的合約 JSON 檔 (注意新路徑，因為 deploy.py 現在在根目錄)
contract_path = "blockchain/artifacts/contracts/CampusWall.sol/CampusWall.json"
try:
    with open(contract_path, "r", encoding="utf-8") as f:
        contract_data = json.load(f)
except FileNotFoundError:
    print(f"❌ 找不到合約檔案：{contract_path}，請確認是否已編譯！")
    exit()

# 4. 準備部署 (因為改成無錢包架構，不需要傳入 Merkle Root 了)
print("正在將合約部署至區塊鏈...")
CampusWall = w3.eth.contract(abi=contract_data['abi'], bytecode=contract_data['bytecode'])
tx_hash = CampusWall.constructor().transact()

# 5. 等待部署完成
tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
new_address = tx_receipt.contractAddress
print(f"🎉 部署成功！合約地址: {new_address}")

# 6. 自動更新 .env 檔案
print("🔄 正在自動更新 .env...")
try:
    with open('.env', 'r', encoding='utf-8') as f:
        content = f.read()

    # 精準尋找並替換 CONTRACT_ADDRESS="..."
    content = re.sub(r'CONTRACT_ADDRESS\s*=\s*["\'].*?["\']', f'CONTRACT_ADDRESS="{new_address}"', content)

    with open('.env', 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ .env 更新完成！系統已準備就緒。")
except FileNotFoundError:
    print("⚠️ 找不到 .env 檔案，請記得手動將地址補上去。")