import {ref,shallowRef,watch,onBeforeUnmount} from 'vue';
import {onLoad,onShow,onHide} from '@dcloudio/uni-app';
import {useUserStore} from '../store/user';
import {useStudioNative,provideStudioNative} from './studio-native';
import {registerWorkspace,takeWorkspace,workspaceCommand,workspaceRoutes,workspaceUrl,type WorkspaceCommand,type WorkspaceKind} from './studio-workspace-router';
export function useWorkspace(kind:WorkspaceKind){
 const user=useUserStore(),native=useStudioNative();provideStudioNative(native);
 const root=workspaceRoutes[kind].home,tab=ref('home'),visible=ref(false),visited=ref<Record<string,boolean>>({home:true}),query=shallowRef<Record<string,string>>({}),scope=ref(0);
 let unregister:undefined|(()=>void);
 const apply=(command:WorkspaceCommand)=>{
  if(!Object.keys(workspaceRoutes[kind]).includes(command.tab))return;
  query.value=command.query;visited.value[command.tab]=true;tab.value=command.tab;
  // A hidden input must not keep its keyboard covering the next panel.
  uni.hideKeyboard?.();
 };
 onLoad(q=>{const initial=workspaceCommand(workspaceUrl(root,q||{}));if(initial)apply(initial);});
 onShow(()=>{unregister?.();unregister=registerWorkspace(root,apply);const pending=takeWorkspace(root);if(pending)apply(pending);visible.value=true;});
 onHide(()=>{visible.value=false;unregister?.();unregister=undefined;});
 onBeforeUnmount(()=>{visible.value=false;unregister?.();});
 // No retained private UI or drafts may cross a logout/account change.
 watch(()=>user.token,()=>{scope.value++;visited.value={[tab.value]:true};},{flush:'sync'});
 return {...native,tab,visible,visited,query,scope};
}
