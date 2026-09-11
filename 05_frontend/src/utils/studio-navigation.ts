let navigating=false,queued='',target='',sequence=0;
function finish(id:number){
 if(!navigating||id!==sequence)return;
 navigating=false;const next=queued;queued='';
 if(next)navigateStudio(next);
}
export function studioPageShown(route:string){
 if(!navigating)return;
 // Navigation can be interrupted by a redirect/logout before complete fires.
 if(route!==target)queued='';
 finish(sequence);
}
export function navigateStudio(url:string){
 if(navigating){queued=url;return;}
 const pages=getCurrentPages(),route=url.replace(/^\//,'');
 if(pages[pages.length-1]?.route===route)return;
 const previous=pages.map(page=>page.route).lastIndexOf(route);
 navigating=true;target=route;const id=++sequence;
 const complete=()=>finish(id);
 if(previous>=0)uni.navigateBack({delta:pages.length-1-previous,complete});
 else if(pages.length<8)uni.navigateTo({url,complete});
 else uni.redirectTo({url,complete});
}
