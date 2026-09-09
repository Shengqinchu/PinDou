export async function writeClipboard(text:string):Promise<boolean> {
  try {if(navigator.clipboard){await navigator.clipboard.writeText(text);return true;}} catch { /* WebView may deny Clipboard API; try its native copy command. */ }
  const focused=document.activeElement as HTMLElement|null;
  const selection=getSelection(),ranges=selection?Array.from({length:selection.rangeCount},(_,i)=>selection.getRangeAt(i).cloneRange()):[];
  const input=document.createElement('textarea');input.value=text;input.readOnly=true;
  Object.assign(input.style,{position:'fixed',top:'0',left:'0',width:'1px',height:'1px',opacity:'0',fontSize:'16px'});
  document.body.append(input);input.focus({preventScroll:true});input.select();input.setSelectionRange(0,text.length);
  let copied=false;try{copied=document.execCommand('copy');}catch { /* Offer an explicit selectable fallback. */ }
  input.remove();focused?.focus({preventScroll:true});
  if(selection){selection.removeAllRanges();for(const range of ranges)selection.addRange(range);}
  return copied;
}
