@echo off
rem ============================================================
rem  E-Resume launcher (Windows)
rem  Usage:  eresume.bat <command> [args...]
rem  Examples:
rem    eresume.bat init
rem    eresume.bat profile
rem    eresume.bat prefs
rem    eresume.bat job scrape -k python --city Beijing
rem    eresume.bat match "<job text>"
rem    eresume.bat hr "<hr message>"
rem  Sets UTF-8 output so Chinese displays correctly.
rem ============================================================
chcp 65001 >nul
set PYTHONIOENCODING=utf-8

rem ---- Optional LLM provider (uncomment and fill in) ----
rem set ERESUME_PROVIDER=zhipu
rem set ERESUME_API_KEY=sk-xxxx
rem Providers: openai deepseek qwen kimi zhipu minimax hunyuan ernie ollama vllm
rem Run "eresume.bat config" to see all presets.

rem User data directory (default: ~/.eresume)
set ERESUME_DIR=%USERPROFILE%\.eresume
cd /d "%~dp0"
python -m eresume %*
