@echo off
REM Double-click to launch the Jarvis dashboard on Windows.
REM Installs dependencies if needed, starts the server, and opens your browser.
cd /d "%~dp0"
where py >nul 2>nul && (py dashboard\start.py) || (python dashboard\start.py)
pause
