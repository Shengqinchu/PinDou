import {workspaceCommand,queueWorkspace,showWorkspace} from './studio-workspace-router';
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
 const pages=getCurrentPages();
 const command=workspaceCommand(url),route=command?.root||url.replace(/^\//,'').split('?')[0];
 if(navigating&&pages[pages.length-1]?.route===target){navigating=false;queued='';}
 if(navigating){queued=url;return;}
 if(command){queueWorkspace(command);if(pages[pages.length-1]?.route===route){showWorkspace(command);return;}}
 if(pages[pages.length-1]?.route===route)return;
 const previous=pages.map(page=>page.route).lastIndexOf(route);
 navigating=true;target=route;const id=++sequence;
 const complete=()=>finish(id);
 if(previous>=0)uni.navigateBack({delta:pages.length-1-previous,complete});
 else if(command&&pages[pages.length-1]?.route===url.replace(/^\//,'').split('?')[0])uni.redirectTo({url:'/'+route,complete});
 else if(pages.length<8)uni.navigateTo({url:command?'/'+route:url,complete});
 else uni.redirectTo({url:command?'/'+route:url,complete});
}
