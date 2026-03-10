@echo off
cd /d %~dp0
echo Cloudflare Tunnel 시작중...
"C:\Users\USER\AppData\Local\Microsoft\WinGet\Packages\Cloudflare.cloudflared_Microsoft.Winget.Source_8wekyb3d8bbwe\cloudflared.exe" tunnel --url http://localhost:5050
pause
