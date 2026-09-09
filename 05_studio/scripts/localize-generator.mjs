// One-time source migration. The dictionary remains archived, editable bilingual content.
import fs from 'node:fs';import path from 'node:path';import {fileURLToPath} from 'node:url';
import {parse} from '@vue/compiler-sfc';import {baseParse} from '@vue/compiler-dom';import ts from 'typescript';
const root=fileURLToPath(new URL('../../',import.meta.url)),source=path.join(root,'05_generator/src'),catalog=new Map();
const cjk=/[\u3400-\u9fff]/;
function record(text,file){if(cjk.test(text)&&!text.includes('[PinDou]')){const old=catalog.get(text)||[];if(!old.includes(file))old.push(file);catalog.set(text,old);}}
function scriptStrings(script,file){const ast=ts.createSourceFile(file,script,ts.ScriptTarget.Latest,true);function walk(node){
 if(ts.isStringLiteral(node)||ts.isNoSubstitutionTemplateLiteral(node))record(node.text,file);
 if(ts.isTemplateExpression(node)){let s=node.head.text;node.templateSpans.forEach((span,i)=>s+=`{v${i}}`+span.literal.text);record(s,file);}
 ts.forEachChild(node,walk);
}walk(ast);}
for(const p of fs.readdirSync(source,{recursive:true}).map(p=>path.join(source,p)).filter(p=>/\.(vue|ts)$/.test(p)&&fs.statSync(p).isFile())){
 let text=fs.readFileSync(p,'utf8'),file=path.relative(source,p).replaceAll('\\','/');
 if(p.endsWith('.ts')){scriptStrings(text,file);continue;}
 const {descriptor}=parse(text),template=descriptor.template;if(!template)continue;
 scriptStrings(descriptor.scriptSetup?.content||'',file);
 const edits=[],start=template.loc.start.offset;function edit(node,replacement){edits.push({start:start+node.loc.start.offset,end:start+node.loc.end.offset,text:replacement});}
 function walk(node){
  if(node.type===2&&cjk.test(node.content)){const value=node.content.trim().replace(/\s+/g,' ');record(value,file);edit(node,`{{ gt(${JSON.stringify(value)}) }}`);}
  if(node.type===5){const value=node.content.content;scriptStrings('const value=('+value+');',file);if(!/^gt\(/.test(value)&&!/(?:nickname|\.email|\.name\b|(?:work|artwork)\.title\b|selectedFile\.name)/.test(value))edit(node,`{{ gt(${value}) }}`);}
  if(node.type===1)for(const prop of node.props||[]){
   if(prop.type===6&&prop.value&&['title','alt','aria-label','placeholder'].includes(prop.name)&&cjk.test(prop.value.content)){
    record(prop.value.content,file);edit(prop,`:${prop.name}='gt(${JSON.stringify(prop.value.content)})'`);
   }else if(prop.type===7&&prop.name==='bind'&&prop.arg&&['title','alt','aria-label','placeholder'].includes(prop.arg.content)&&prop.exp&&!prop.exp.content.startsWith('gt(')){
    scriptStrings('const value=('+prop.exp.content+');',file);
    edit(prop,`:${prop.arg.content}="gt(${prop.exp.content.replaceAll('"','&quot;')})"`);
   }
  }
  for(const child of node.children||[])walk(child);
 }
 walk(baseParse(template.content));
 edits.sort((a,b)=>b.start-a.start).forEach(e=>{text=text.slice(0,e.start)+e.text+text.slice(e.end);});
 if(!text.includes("import { gt }"))text=text.replace('<script setup lang="ts">',`<script setup lang="ts">\nimport { gt } from '${file.includes('/')?'../':'./'}i18n';`);
 text=text.replace(/window\.confirm\(([^;]+)\)/g,(all,arg)=>arg.startsWith('gt(')?all:`window.confirm(gt(${arg}))`);
 fs.writeFileSync(p,text);
}
const target=path.join(root,'artifacts/generator-integration');fs.mkdirSync(target,{recursive:true});
fs.writeFileSync(path.join(target,'zh-catalog.json'),JSON.stringify([...catalog].map(([zh,files],i)=>({i,zh,files})),null,2));
console.log('Collected',catalog.size,'source phrases');
