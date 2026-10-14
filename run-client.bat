@echo off
echo Starting PK-Hub Next.js Client...
cd client
if not exist node_modules (
    echo Installing dependencies...
    npm install
)
npm run dev

