@echo off
:: 番茄钟 - 启动脚本
:: 双击此文件运行

title 番茄钟
cd /d "%~dp0"
start "" "D:\Python\pythonw.exe" "%~dp0pomodoro.py"
