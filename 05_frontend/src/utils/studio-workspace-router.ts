// Keep the existing public page paths as aliases, without rebuilding a page
// for each bottom-navigation click. Detail pages keep their native back stack.
export const workspaceRoutes={
 customer:{home:'pages/studio/home',bookings:'pages/studio/reservations',account:'pages/auth/studio-account'},
 admin:{home:'pages/studio/manage',reservations:'pages/studio/manage-reservations',messages:'pages/studio/manage-messages',finance:'pages/studio/manage-finance'},
} as const;
export type WorkspaceKind=keyof typeof workspaceRoutes;
export type WorkspaceCommand={root:string;tab:string;query:Record<string,string>};
const pending=new Map<string,WorkspaceCommand>(),handlers=new Map<string,(command:WorkspaceCommand)=>void>();
export function workspaceCommand(url:string):WorkspaceCommand|undefined{
 const [path,search='']=url.replace(/^\//,'').split('?'),query:Record<string,string>={};
 for(const part of search.split('&')){const [key,...value]=part.split('=');if(key)try{query[decodeURIComponent(key)]=decodeURIComponent(value.join('='));}catch{}}
 for(const routes of Object.values(workspaceRoutes)){
  const entry=Object.entries(routes).find(([,route])=>route===path);
  if(entry){const tab=path===routes.home&&Object.keys(routes).includes(query._tab)?query._tab:entry[0];delete query._tab;return {root:routes.home,tab,query};}
 }
}
export function queueWorkspace(command:WorkspaceCommand){pending.set(command.root,command);}
export function takeWorkspace(root:string){const command=pending.get(root);pending.delete(root);return command;}
export function showWorkspace(command:WorkspaceCommand){const handler=handlers.get(command.root);if(!handler)return false;pending.delete(command.root);handler(command);return true;}
export function registerWorkspace(root:string,handler:(command:WorkspaceCommand)=>void){
 handlers.set(root,handler);return ()=>{if(handlers.get(root)===handler)handlers.delete(root);};
}
export function workspaceUrl(root:string,query:Record<string,unknown>){return '/'+root+'?'+Object.entries(query).filter(([,v])=>typeof v==='string').map(([k,v])=>encodeURIComponent(k)+'='+encodeURIComponent(String(v))).join('&');}
