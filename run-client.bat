@echo off
echo Starting PK-Hub Next.js Client...
cd /d "%~dp0client"
if not exist node_modules (
    echo Installing dependencies...
    npm install
)
npm run dev

