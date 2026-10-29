@echo off
echo Starting PK-Hub Next.js Client (production build)...
cd /d "%~dp0client"
if not exist node_modules (
    echo Installing dependencies...
    npm install
)
call npm run build
if errorlevel 1 exit /b 1
npm start
