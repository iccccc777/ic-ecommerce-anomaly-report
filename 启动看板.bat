@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 正在启动 Streamlit 看板...
.\.venv\Scripts\python.exe -m streamlit run python\08_streamlit_dashboard.py --server.port 8501
pause
