// First-party operational signals: no messages, stack traces, queries, user IDs
// or page text leave the browser. Cap and deduplicate within the current page.
export function installDiagnostics() {
  const sent=new Set<string>();
  function record(kind:'error'|'unhandledrejection',error:unknown,filename='',line=0) {
    if(sent.size>=5)return;
    const name=error instanceof Error&&['Error','TypeError','ReferenceError','SyntaxError','RangeError'].includes(error.name)?error.name:'Other';
    const asset=/\/studio-assets\/([A-Za-z0-9_-]+\.js)(?:$|[?#])/.exec(filename)?.[1]||'';
    if(kind==='error'&&!asset)return; // Browser extensions and third-party beacons are outside this app.
    const first='/'+location.pathname.split('/').filter(Boolean)[0];
    const page=location.pathname==='/'?'/':['/visit','/details','/journal','/shop','/manage','/reservation','/order'].includes(first)?first:'/other';
    const body={kind,name,page,asset,line:Number.isInteger(line)?line:0},key=JSON.stringify(body);
    if(sent.has(key))return;sent.add(key);
    void fetch('/studio-api/client-event',{method:'POST',headers:{'Content-Type':'application/json'},body:key,keepalive:true}).catch(()=>{});
  }
  const failure=(event:ErrorEvent)=>record('error',event.error,event.filename,event.lineno);
  const rejected=(event:PromiseRejectionEvent)=>record('unhandledrejection',event.reason);
  window.addEventListener('error',failure);window.addEventListener('unhandledrejection',rejected);
  return()=>{window.removeEventListener('error',failure);window.removeEventListener('unhandledrejection',rejected);};
}
