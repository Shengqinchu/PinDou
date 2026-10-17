import {navigateStudio} from './studio-navigation';
// A quick tap still lets the press reach its low point before the screen changes,
// like the website's short-tap rule. 90ms stays under the ~100ms users notice as delay,
// and taps landing inside the window are ignored so a double tap cannot open a page twice.
export const PRESS_ACK_MS=90;
let waiting=false;
export function afterPress(action:()=>void){
 if(waiting)return;waiting=true;
 setTimeout(()=>{waiting=false;action();},PRESS_ACK_MS);
}
export const pressTo=(url:string)=>afterPress(()=>uni.navigateTo({url}));
export const pressNavigate=(url:string)=>afterPress(()=>navigateStudio(url));
