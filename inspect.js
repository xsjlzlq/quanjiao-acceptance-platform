const fs = require('fs');
const code = fs.readFileSync('backend/main.py', 'utf8');
const m = code.match(/@app\.get\("\/api\/hierarchy"\)[\s\S]*?return \{"code": 200[\s\S]*?\}/);
console.log(m ? m[0] : 'not found');