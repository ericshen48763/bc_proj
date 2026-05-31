@echo off
chcp 65001 > nul
echo ======================================================
echo BlockWhisper 一鍵啟動腳本 (Windows 版)
echo ======================================================

echo [1/4] 正在啟動 Hardhat 區塊鏈節點...
cd blockchain
start "Hardhat Node" cmd /c "npx hardhat node"
timeout /t 3 /nobreak > nul
echo [成功] 本地節點已啟動！

echo 正在編譯智能合約...
call npx hardhat compile > nul
cd ..

echo.
echo [2/4] 正在執行自動部署與更新 .env ...
call venv\Scripts\activate.bat
echo ------------------------------------------------------
python deploy.py
echo ------------------------------------------------------

echo.
echo [3/4] 正在啟動 FastAPI 伺服器...
start "FastAPI Server" cmd /c "call venv\Scripts\activate.bat && uvicorn api:app --reload"

echo [4/4] 正在啟動 Streamlit 網頁介面...
start "Streamlit App" cmd /c "call venv\Scripts\activate.bat && streamlit run app.py"

echo.
echo ======================================================
echo [完成] 所有服務已全面啟動！
echo 注意:系統已幫您開啟了三個新的黑色視窗。
echo 若要關閉系統，請直接將那三個視窗打叉關閉即可。
echo ======================================================
pause