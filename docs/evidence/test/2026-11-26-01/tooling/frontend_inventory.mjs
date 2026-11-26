import fs from 'node:fs';
import path from 'node:path';
import { parse } from './checkout/frontend/node_modules/@babel/parser/lib/index.js';
const root=path.join(import.meta.dirname,'checkout');
const records=[];
function walk(node,visit){ if(!node||typeof node!=='object')return; if(Array.isArray(node)){for(const n of node)walk(n,visit);return;}if(node.type)visit(node);for(const [k,v] of Object.entries(node))if(!['loc','start','end','extra','comments','tokens'].includes(k)&&v&&typeof v==='object')walk(v,visit); }
function scan(dir){for(const e of fs.readdirSync(dir,{withFileTypes:true})){const p=path.join(dir,e.name);if(e.isDirectory())scan(p);else if(e.name.endsWith('.test.js')){
 const source=fs.readFileSync(p,'utf8');const ast=parse(source,{sourceType:'module',plugins:['importAttributes']});
 function descend(node,suites=[]){if(!node||typeof node!=='object')return;if(Array.isArray(node)){node.forEach(n=>descend(n,suites));return;}
  if(node.type==='CallExpression'&&node.callee.type==='Identifier'&&['it','test','describe'].includes(node.callee.name)){
   const title=node.arguments[0]?.value; const cb=node.arguments[1];
   if(node.callee.name==='describe'){descend(cb,[...suites,title]);return;}
   const asserts=[];walk(cb,n=>{if(n.type==='CallExpression'&&n.callee.type==='MemberExpression'){
    const raw=source.slice(n.start,n.end);if(raw.startsWith('expect(')&&/\.to[A-Z]|\.rejects|\.resolves/.test(raw))asserts.push(raw);
   }});
   const steps=(cb?.body?.body||[]).map(stmt=>source.slice(stmt.start,stmt.end)).filter(s=>!/^\s*(?:await\s+)?expect\(/.test(s));
   records.push({file:path.relative(root,p).replaceAll('\\','/'),title,suites,fullName:[...suites,title].join(' '),line:node.loc.start.line,assertions:[...new Set(asserts)],steps,source:source.slice(node.start,node.end)});return;
  }
  for(const [k,v]of Object.entries(node))if(!['loc','start','end','extra','comments','tokens'].includes(k)&&v&&typeof v==='object')descend(v,suites);
 }
 descend(ast);
}}}
scan(path.join(root,'frontend/src'));
fs.writeFileSync('D:/DATA/university/3_1/Software Engineering/11.26/study-room/docs/evidence/test/2026-11-26-full-suite/frontend-source-inventory.json',JSON.stringify(records,null,2));
console.log(JSON.stringify({records:records.length,files:new Set(records.map(r=>r.file)).size}));
