@echo off
chcp 65001 > nul

echo ======================================================
echo 系統環境初始化 (Windows 版)
echo ======================================================

echo.
echo [1/2] 正在安裝區塊鏈相依套件 (Node.js)...
if exist "blockchain" (
    cd blockchain
    call npm install --legacy-peer-deps
    cd ..
    echo [成功] 區塊鏈環境建置完成！
) else (
    echo [警告] 找不到 blockchain 資料夾。
)

echo.
echo [2/2] 正在建立 Python 虛擬環境...
if not exist "venv" (
    python -m venv venv
    echo [成功] 虛擬環境 venv 建立成功！
)

echo 正在安裝 Python 套件...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip > nul
:: 請確認你的專案根目錄有 requirements.txt 這個檔案！
pip install -r requirements.txt
call venv\Scripts\deactivate.bat
echo [成功] Python 環境建置完成！

echo.
echo ======================================================
echo [完成] 所有環境建置完畢！
echo ======================================================
pause