<script setup lang="ts">
import {computed,getCurrentInstance,nextTick,ref,shallowRef} from 'vue';
import {onLoad,onReady,onUnload} from '@dcloudio/uni-app';
import StudioShell from '../../components/StudioShell.vue';
import StudioGlyph from '../../components/StudioGlyph.vue';
import {useStudioNative} from '../../utils/studio-native';
import {studioWords} from '../../utils/studio-content';
import {patternState,savePattern,PatternError,type PatternResult} from '../../utils/pattern-tool';
// The website editor's pure editing helpers and MARD chart, shared rather than copied.
import {applyBatchPatch,clonePattern,cloneColor,colorTextFill,fontSizeForCode,paletteRowsForPattern,recalculatePattern,type CellPatch} from '../../../../05_generator/src/utils/patternEditing';
import mard from '../../../../05_generator/src/assets/colormap/mard-5mm.json';
type Color={brand:string;code:string;name_cn:string;hex:string;rgb:[number,number,number];bead_diameter_mm?:number};
type Tool='move'|'paint'|'erase'|'replace';
const {language,keyboardOpen,shellStyle,say,changeLanguage,width}=useStudioNative();
const words=(key:string)=>say(studioWords('miniapp',key));
const instance=getCurrentInstance();
const result=shallowRef<PatternResult|null>(null),sheet=shallowRef<any>(null);
const tool=ref<Tool>('paint'),color=ref<Color|null>(null),zoom=ref(0),saving=ref(false),errorCode=ref(''),paletteOpen=ref(false),series=ref('A'),replaceSource=ref<Color|null>(null);
const undoStack:CellPatch[][]=[],redoStack:CellPatch[][]=[];const history=ref(0);
const columns=computed(()=>sheet.value?.grid?.[0]?.length||1),rows=computed(()=>sheet.value?.grid?.length||1);
// Zoom 0 fits the viewport width; each step enlarges cells for precise taps.
const fitCell=computed(()=>Math.max(4,Math.floor((width.value-24)/columns.value)));
const cell=computed(()=>Math.min(36,fitCell.value*[1,2,3][zoom.value]));
const canvasStyle=computed(()=>({width:columns.value*cell.value+'px',height:rows.value*cell.value+'px'}));
const used=computed(()=>paletteRowsForPattern(sheet.value).map((row:any)=>({...row.color,count:row.count})) as (Color&{count:number})[]);
const chart=(mard as (Color&{category:string})[]).map(({category,...rest})=>rest as Color);
const seriesList=[...new Set(chart.map(item=>item.code.replace(/\d.*$/,'')))];
const seriesColors=computed(()=>chart.filter(item=>item.code.replace(/\d.*$/,'')===series.value));
const dirty=computed(()=>history.value>0&&undoStack.length>0);
let canvas:any=null,context:any=null,ratio=1,painting:CellPatch[]=[],lastKey='',rect={left:0,top:0},scroll={left:0,top:0};

onLoad(()=>{
 const current=patternState.get();if(!current?.sheet?.grid){uni.navigateBack();return;}
 result.value=current;sheet.value=recalculatePattern(clonePattern(current.sheet));
 color.value=used.value[0]?cloneColor(used.value[0]):cloneColor(chart[0]);
 series.value=color.value.code.replace(/\d.*$/,'')||'A';
});
onReady(()=>void setupCanvas());
onUnload(()=>toggleLeaveGuard(false));

function setupCanvas(){
 return new Promise<void>(resolve=>uni.createSelectorQuery().in(instance?.proxy).select('#pattern-edit-canvas').fields({node:true,size:true,rect:true}).exec(res=>{
  const info=res?.[0];if(!info?.node){resolve();return;}
  canvas=info.node;context=canvas.getContext('2d');rect={left:info.left||0,top:info.top||0};
  // #ifndef H5
  // Native 2D canvases need manual high-DPI sizing; large boards stay under common size limits.
  const pixels=Math.max(columns.value,rows.value)*cell.value;
  ratio=Math.max(1,Math.min(uni.getWindowInfo?.().pixelRatio||2,4096/pixels));
  canvas.width=columns.value*cell.value*ratio;canvas.height=rows.value*cell.value*ratio;context.setTransform(ratio,0,0,ratio,0,0);
  // #endif
  drawAll();resolve();
 }));
}
function drawCell(r:number,c:number){
 if(!context)return;const size=cell.value,value=sheet.value.grid[r][c] as Color|null,x=c*size,y=r*size;
 context.fillStyle=value?value.hex:((r+c)%2?'#f7f9fa':'#ffffff');context.fillRect(x,y,size,size);
 context.strokeStyle='#dfe7ec';context.lineWidth=0.5;context.strokeRect(x+0.25,y+0.25,size-0.5,size-0.5);
 if(value&&size>=18){context.fillStyle=colorTextFill(value as any);context.font=`600 ${fontSizeForCode(value.code,size)}px sans-serif`;context.textAlign='center';context.textBaseline='middle';context.fillText(value.code,x+size/2,y+size/2+0.5);}
}
function drawAll(){
 if(!context||!sheet.value)return;const size=cell.value;context.clearRect(0,0,columns.value*size,rows.value*size);
 for(let r=0;r<rows.value;r++)for(let c=0;c<columns.value;c++)drawCell(r,c);
 // Every tenth line is darker so beads can be counted on a board.
 context.strokeStyle='#e7a1a1';context.lineWidth=1;
 for(let i=10;i<columns.value;i+=10){context.beginPath();context.moveTo(i*size,0);context.lineTo(i*size,rows.value*size);context.stroke();}
 for(let i=10;i<rows.value;i+=10){context.beginPath();context.moveTo(0,i*size);context.lineTo(columns.value*size,i*size);context.stroke();}
}
function point(event:any){
 const touch=event.touches?.[0]||event.changedTouches?.[0];if(!touch)return null;
 const x=typeof touch.x==='number'?touch.x:touch.clientX-rect.left+scroll.left,y=typeof touch.y==='number'?touch.y:touch.clientY-rect.top+scroll.top;
 const c=Math.floor(x/cell.value),r=Math.floor(y/cell.value);
 return r>=0&&c>=0&&r<rows.value&&c<columns.value?{r,c}:null;
}
function touch(event:any,start:boolean){
 if(tool.value==='move')return;const at=point(event);if(!at)return;
 if(tool.value==='replace'){if(start)pickReplaceSource(sheet.value.grid[at.r][at.c]);return;}
 const key=at.r+':'+at.c;if(!start&&key===lastKey)return;lastKey=key;
 const before=sheet.value.grid[at.r][at.c] as Color|null,after=tool.value==='erase'?null:color.value;
 if((before?.code||'')===(after?.code||''))return;
 // Paint in place for responsiveness; counts are recalculated once the stroke ends.
 sheet.value.grid[at.r][at.c]=after?cloneColor(after as any):null;painting.push({row:at.r,col:at.c,before:before?cloneColor(before as any):null,after:after?cloneColor(after as any):null});drawCell(at.r,at.c);
}
function strokeEnd(){
 lastKey='';if(!painting.length)return;
 undoStack.push(painting);if(undoStack.length>240)undoStack.shift();redoStack.length=0;painting=[];
 sheet.value=recalculatePattern(sheet.value);history.value++;toggleLeaveGuard(true);
}
function undo(){const step=undoStack.pop();if(!step)return;redoStack.push(step);sheet.value=applyBatchPatch(sheet.value,step,false);history.value++;drawAll();}
function redo(){const step=redoStack.pop();if(!step)return;undoStack.push(step);sheet.value=applyBatchPatch(sheet.value,step,true);history.value++;drawAll();}
async function setZoom(step:number){const next=Math.max(0,Math.min(2,zoom.value+step));if(next===zoom.value)return;zoom.value=next;await nextTick();await setupCanvas();}
function choose(next:Color){
 if(replaceSource.value){replaceAll(replaceSource.value,next);return;}
 color.value=cloneColor(next as any);paletteOpen.value=false;if(tool.value!=='paint')tool.value='paint';
}
function pickReplaceSource(source:Color|null){
 if(!source)return;replaceSource.value=cloneColor(source as any);series.value=source.code.replace(/\d.*$/,'')||series.value;paletteOpen.value=true;
}
function replaceAll(source:Color,target:Color){
 paletteOpen.value=false;const count=sheet.value.color_counts[source.code]||0;
 if(source.code===target.code||!count){replaceSource.value=null;return;}
 uni.showModal({content:words('pattern_replace_confirm').replace('{v0}',source.code).replace('{v1}',String(count)).replace('{v2}',target.code),confirmText:words('pattern_tool_replace'),cancelText:words('cancel'),success:value=>{
  replaceSource.value=null;if(!value.confirm)return;
  const patches:CellPatch[]=[];sheet.value.grid.forEach((line:(Color|null)[],r:number)=>line.forEach((item,c)=>{if(item?.code===source.code)patches.push({row:r,col:c,before:cloneColor(item as any),after:cloneColor(target as any)});}));
  undoStack.push(patches);redoStack.length=0;sheet.value=applyBatchPatch(sheet.value,patches,true);history.value++;color.value=cloneColor(target as any);tool.value='paint';toggleLeaveGuard(true);drawAll();
 }});
}
function selectTool(next:Tool){tool.value=next;replaceSource.value=null;if(next==='replace')uni.showToast({title:words('pattern_replace_hint'),icon:'none'});}
function toggleLeaveGuard(on:boolean){
 // #ifdef MP-WEIXIN
 if(on)uni.enableAlertBeforeUnload?.({message:words('pattern_unsaved')});else uni.disableAlertBeforeUnload?.();
 // #endif
}
async function save(){
 if(!result.value||saving.value)return;saving.value=true;errorCode.value='';
 try{const next=await savePattern(result.value,recalculatePattern(sheet.value));patternState.set(next);undoStack.length=0;redoStack.length=0;toggleLeaveGuard(false);uni.navigateBack();}
 catch(error){errorCode.value=error instanceof PatternError?error.code:'pattern_error';}
 finally{saving.value=false;}
}
const colorInUse=computed(()=>used.value.some(item=>item.code===color.value?.code));
function onScroll(event:any){scroll={left:event.detail.scrollLeft,top:event.detail.scrollTop};}
function openPalette(){replaceSource.value=null;paletteOpen.value=true;}
function closePalette(){paletteOpen.value=false;replaceSource.value=null;}
function chipTap(item:Color){if(tool.value==='replace')pickReplaceSource(item);else choose(item);}
const tools:{id:Tool;icon:string;key:string}[]=[{id:'move',icon:'move',key:'pattern_tool_move'},{id:'paint',icon:'brush',key:'pattern_tool_paint'},{id:'erase',icon:'eraser',key:'pattern_tool_erase'},{id:'replace',icon:'swap',key:'pattern_tool_replace'}];
</script>
<template>
 <StudioShell id="studio-pattern-edit-shell" fitted workspace :language="language" :keyboard-open="keyboardOpen" :shell-style="shellStyle" @language="changeLanguage">
  <view class="studio-editor">
   <view class="studio-editor-status"><text class="studio-native-subtitle">{{words('pattern_edit')}}</text><text class="studio-native-small">{{sheet?words('pattern_counts').replace('{v0}',String(sheet.bead_total)).replace('{v1}',String(used.length)):''}}</text></view>
   <scroll-view class="studio-editor-viewport" :scroll-x="tool==='move'" :scroll-y="tool==='move'" :show-scrollbar="false" @scroll="onScroll">
    <canvas id="pattern-edit-canvas" type="2d" class="studio-editor-canvas" :style="canvasStyle" :disable-scroll="tool!=='move'" @touchstart="touch($event,true)" @touchmove="touch($event,false)" @touchend="strokeEnd" @touchcancel="strokeEnd"/>
   </scroll-view>
   <view class="studio-editor-tools">
    <button v-for="item in tools" :key="item.id" class="studio-editor-tool" :class="{'studio-editor-tool--active':tool===item.id}" hover-class="studio-native-pressed" :hover-stay-time="180" :hover-start-time="0" :aria-pressed="tool===item.id" @tap="selectTool(item.id)"><StudioGlyph :name="item.icon" :size="19"/><text>{{words(item.key)}}</text></button>
    <view class="studio-editor-tool-gap"/>
    <button class="studio-editor-icon" hover-class="studio-native-pressed" :hover-stay-time="180" :hover-start-time="0" :disabled="!history||!undoStack.length" :aria-label="words('pattern_undo')" @tap="undo"><StudioGlyph name="undo" :size="19"/></button>
    <button class="studio-editor-icon" hover-class="studio-native-pressed" :hover-stay-time="180" :hover-start-time="0" :disabled="!history||!redoStack.length" :aria-label="words('pattern_redo')" @tap="redo"><StudioGlyph name="redo" :size="19"/></button>
    <button class="studio-editor-icon" hover-class="studio-native-pressed" :hover-stay-time="180" :hover-start-time="0" :disabled="zoom===0" :aria-label="words('pattern_zoom_out')" @tap="setZoom(-1)"><StudioGlyph name="minus" :size="19"/></button>
    <button class="studio-editor-icon" hover-class="studio-native-pressed" :hover-stay-time="180" :hover-start-time="0" :disabled="zoom===2" :aria-label="words('pattern_zoom_in')" @tap="setZoom(1)"><StudioGlyph name="plus" :size="19"/></button>
   </view>
   <scroll-view class="studio-editor-colors" scroll-x :show-scrollbar="false">
    <view class="studio-editor-color-row">
     <button v-for="item in used" :key="item.code" class="studio-editor-chip" :class="{'studio-editor-chip--active':tool==='paint'&&color?.code===item.code}" hover-class="studio-native-pressed" :hover-stay-time="180" :hover-start-time="0" @tap="chipTap(item)"><view class="studio-pattern-swatch" :style="{background:item.hex}"/><text class="studio-pattern-code">{{item.code}}</text><text class="studio-pattern-count">{{item.count}}</text></button>
     <button v-if="color&&!colorInUse" class="studio-editor-chip studio-editor-chip--active" hover-class="studio-native-pressed" :hover-stay-time="180" :hover-start-time="0"><view class="studio-pattern-swatch" :style="{background:color.hex}"/><text class="studio-pattern-code">{{color.code}}</text></button>
     <button class="studio-editor-chip" hover-class="studio-native-pressed" :hover-stay-time="180" :hover-start-time="0" @tap="openPalette"><StudioGlyph name="palette" :size="18"/><text class="studio-pattern-code">{{words('pattern_more_colors')}}</text></button>
    </view>
   </scroll-view>
   <text v-if="errorCode" class="studio-native-error" role="alert">{{words(errorCode)}}</text>
  </view>
  <template #actions><view class="studio-visit-actions"><button class="studio-native-primary" hover-class="studio-native-pressed" :hover-stay-time="180" :hover-start-time="0" :disabled="saving||!dirty" :loading="saving" @tap="save"><StudioGlyph name="check"/><text class="studio-native-primary-label">{{words(saving?'pattern_saving':'pattern_save_edit')}}</text></button></view></template>
  <template #overlay>
   <view v-if="paletteOpen" class="studio-editor-sheet-mask" @tap.self="closePalette">
    <view class="studio-editor-sheet">
     <view class="studio-editor-sheet-head"><text class="studio-native-subtitle">{{replaceSource?words('pattern_replace_to').replace('{v0}',replaceSource.code):words('pattern_pick_color')}}</text><button class="studio-editor-icon" hover-class="studio-native-pressed" :hover-stay-time="180" :hover-start-time="0" :aria-label="words('cancel')" @tap="closePalette"><StudioGlyph name="close" :size="18"/></button></view>
     <scroll-view scroll-x :show-scrollbar="false" class="studio-editor-series" :scroll-into-view="'series-'+series" :scroll-with-animation="false"><view class="studio-editor-color-row"><button v-for="name in seriesList" :id="'series-'+name" :key="name" class="studio-editor-series-tab" :class="{'studio-editor-series-tab--active':series===name}" hover-class="studio-native-pressed" :hover-stay-time="180" :hover-start-time="0" @tap="series=name">{{name}}</button></view></scroll-view>
     <scroll-view scroll-y class="studio-editor-swatches"><view class="studio-editor-swatch-grid"><button v-for="item in seriesColors" :key="item.code" class="studio-editor-swatch" :class="{'studio-editor-swatch--active':color?.code===item.code}" hover-class="studio-native-pressed" :hover-stay-time="180" :hover-start-time="0" @tap="choose(item)"><view class="studio-editor-swatch-color" :style="{background:item.hex}"/><text>{{item.code}}</text></button></view></scroll-view>
    </view>
   </view>
  </template>
 </StudioShell>
</template>
