<script setup lang="ts">
import {computed,onBeforeUnmount,reactive,ref,watch} from 'vue';
import {PhArrowClockwise,PhPlus,PhTrash,PhPencilSimple} from '@phosphor-icons/vue';
import {useDesk} from '../../admin';
import {hamiltonDate,locale,say,formatCopy} from '../../state';
import {contentModule} from '../../content-store';
import defaults from '../../content/business.json';
import {centsFromInput,money,currencyLabel,financePayments,paymentKey,paymentCurrency,type FinanceQuote,type FinanceDraft,type FinanceEntry,type FinancePage} from '../../business-model';
import SlideOver from '../SlideOver.vue';
const copy=contentModule('business',defaults);
const props=defineProps<{active:boolean}>();const {request}=useDesk();
const today=hamiltonDate(),start=ref(today.slice(0,7)+'-01'),end=ref(today),kind=ref('all'),category=ref(''),query=ref(''),page=ref(1),needsAmount=ref(false);
const data=ref<FinancePage>(),busy=ref(false),saving=ref(false),error=ref(''),editError=ref(''),open=ref(false),categoryOpen=ref(false),categoryName=reactive({zh:'',en:''});
const selected=ref<FinanceEntry|null>(null),amount=ref(''),history=ref<any[]>([]),voiding=ref(false),reason=ref('');
const draft=reactive<FinanceDraft>({kind:'expense',category:'experience',occurred_on:today,customer_name:'',items:[''],amount_cents:null,currency:'CAD',payment_method:'',note:''});
const quote=ref<FinanceQuote>(),fxBusy=ref(false),fxError=ref('');let fxSequence=0;
let sequence=0,timer:ReturnType<typeof setTimeout>|undefined,requestId='';
const label=(key:string)=>say((copy as Record<string,string[]>)[key]||copy.generic_error);
const failure=(e:unknown)=>label((e as {code?:string;message?:string}).code||(e as Error).message);
const categories=computed(()=>data.value?.categories||[]);
const categoryText=(id:string)=>{const item=categories.value.find(c=>c.id===id);return item?item[locale.value==='zh'?'zh':'en']:label('expense');};
const payments=financePayments;
const paymentLabel=(method:string)=>{const key=paymentKey(method);return payments.some(p=>p===key)?label(key):method||'—';};
function paymentChanged(){if(draft.kind==='income')draft.currency=paymentCurrency(draft.payment_method);}
function kindChanged(){draft.category='experience';paymentChanged();}
async function loadQuote(){
 const n=++fxSequence;quote.value=undefined;fxError.value='';fxBusy.value=false;
 if(!open.value||draft.currency!=='CNY')return;
 const saved=selected.value;
 if(saved?.currency==='CNY'&&saved.occurred_on===draft.occurred_on&&saved.fx_rate){quote.value={rate:saved.fx_rate,rate_date:saved.fx_date||draft.occurred_on,source:saved.fx_source};return;}
 fxBusy.value=true;try{const result=await request<FinanceQuote>('/manage/finance/exchange-rate?on='+encodeURIComponent(draft.occurred_on));if(n===fxSequence)quote.value=result;}catch(e){if(n===fxSequence)fxError.value=failure(e);}finally{if(n===fxSequence)fxBusy.value=false;}
}
async function load(){
 const n=++sequence;busy.value=true;error.value='';
 try{const params=new URLSearchParams({start:start.value,end:end.value,kind:kind.value,category:category.value,search:query.value,page:String(page.value),needs_amount:String(needsAmount.value)});
 const result=await request<FinancePage>('/manage/finance?'+params);if(n===sequence)data.value=result;}
 catch(e){if(n===sequence)error.value=failure(e);}finally{if(n===sequence)busy.value=false;}
}
function add(type:'income'|'expense'){
 selected.value=null;requestId=crypto.randomUUID();amount.value='';editError.value='';history.value=[];voiding.value=false;reason.value='';
 Object.assign(draft,{kind:type,category:category.value||'experience',occurred_on:hamiltonDate(),customer_name:'',items:[''],amount_cents:null,currency:'CAD',payment_method:'',note:''});open.value=true;
}
async function edit(entry:FinanceEntry){
 selected.value=entry;amount.value=entry.amount_cents===null?'':(entry.amount_cents/100).toFixed(2);editError.value='';history.value=[];voiding.value=false;reason.value='';
 Object.assign(draft,{kind:entry.kind,category:entry.category,occurred_on:entry.occurred_on,customer_name:entry.customer_name,items:[...entry.items],amount_cents:entry.amount_cents,currency:entry.currency||'CAD',payment_method:paymentKey(entry.payment_method),note:entry.note});open.value=true;
 try{const value=await request<{entry:FinanceEntry;history:any[]}>('/manage/finance/'+entry.id);if(selected.value?.id===entry.id)history.value=value.history;}catch{}
}
async function save(){
 if(saving.value||fxBusy.value)return;if(fxError.value){void loadQuote();return;}const cents=centsFromInput(amount.value);
 if(cents===null&&!(selected.value?.source==='reservation'&&draft.kind==='income'&&!amount.value.trim())){editError.value=label('finance_amount_required');return;}
 const items=draft.items.map(s=>s.trim());if(!items.length||items.some(s=>!s||s.length>200)){editError.value=label('invalid_items');return;}
 saving.value=true;editError.value='';
 try{const payload={...draft,items,amount_cents:cents};
 await request('/manage/finance'+(selected.value?'/'+selected.value.id:''),{method:selected.value?'PUT':'POST',body:JSON.stringify({...payload,...(selected.value?{version:selected.value.version}:{request_id:requestId})})});open.value=false;await load();}
 catch(e){editError.value=failure(e);}finally{saving.value=false;}
}
async function remove(){
 if(!selected.value||!reason.value.trim()||saving.value)return;saving.value=true;editError.value='';
 try{await request('/manage/finance/'+selected.value.id,{method:'DELETE',body:JSON.stringify({version:selected.value.version,reason:reason.value})});open.value=false;await load();}
 catch(e){editError.value=failure(e);}finally{saving.value=false;}
}
async function addCategory(){
 saving.value=true;editError.value='';try{await request('/manage/finance/categories',{method:'POST',body:JSON.stringify(categoryName)});categoryOpen.value=false;Object.assign(categoryName,{zh:'',en:''});await load();}catch(e){editError.value=failure(e);}finally{saving.value=false;}
}
function filtered(){page.value=1;if(props.active)void load();}
watch([start,end,kind,category,needsAmount],filtered);watch(query,()=>{clearTimeout(timer);timer=setTimeout(filtered,250);});
watch([()=>draft.currency,()=>draft.occurred_on,open],()=>void loadQuote());
watch(()=>props.active,value=>{if(value)void load();},{immediate:true});onBeforeUnmount(()=>{sequence++;fxSequence++;clearTimeout(timer);});
defineExpose({refresh:load});
</script>
<template>
 <section class="finance-panel">
  <header class="finance-heading"><h1>{{say(copy.title)}}</h1><div><button class="desk-link" :disabled="busy" @click="load"><PhArrowClockwise/>{{say(copy.refresh)}}</button><button class="desk-button" @click="add('expense')"><PhPlus/>{{say(copy.add_expense)}}</button><button class="desk-button" @click="add('income')"><PhPlus/>{{say(copy.add_income)}}</button></div></header>
  <div class="finance-totals"><div><span>{{say(copy.income)}}</span><strong>{{money(data?.summary.income_cents??0)}}</strong></div><div><span>{{say(copy.expense)}}</span><strong>{{money(data?.summary.expense_cents??0)}}</strong></div><div><span>{{say(copy.balance)}}</span><strong>{{money(data?.summary.balance_cents??0)}}</strong></div></div>
  <p class="finance-help">{{say(copy.cash_note)}} <button v-if="data?.summary.needs_amount" class="desk-link" @click="needsAmount=!needsAmount">{{say(copy.pending_count).replace('{count}',String(data.summary.needs_amount))}}</button></p>
  <div class="finance-filters"><label>{{say(copy.start)}}<input v-model="start" type="date"/></label><label>{{say(copy.end)}}<input v-model="end" type="date"/></label><label>{{say(copy.category)}}<select v-model="kind" @change="category=''"> <option value="all">{{say(copy.all)}}</option><option value="income">{{say(copy.income)}}</option><option value="expense">{{say(copy.expense)}}</option></select></label><label v-if="kind!=='expense'">{{say(copy.income)}}<select v-model="category"><option value="">{{say(copy.all)}}</option><option v-for="c in categories" :value="c.id" :key="c.id">{{locale==='zh'?c.zh:c.en}}</option></select></label><input v-model="query" type="search" :placeholder="say(copy.search)" :aria-label="say(copy.search)"/></div>
  <div class="finance-tools"><label><input v-model="needsAmount" type="checkbox"/>{{say(copy.pending)}}</label><button class="desk-link" @click="categoryOpen=true;editError=''">{{say(copy.new_category)}}</button></div>
  <p v-if="error" class="desk-error" role="alert">{{error}}</p>
  <div class="finance-records"><table v-if="data?.items.length"><thead><tr><th>{{say(copy.date)}}</th><th>{{say(copy.customer)}}</th><th>{{say(copy.items)}}</th><th>{{say(copy.category)}}</th><th>{{say(copy.amount)}}</th><th>{{say(copy.payment)}}</th><th><span class="sr-only">{{say(copy.edit)}}</span></th></tr></thead><tbody><tr v-for="entry in data.items" :key="entry.id"><td :data-label="say(copy.date)">{{entry.occurred_on}}</td><td :data-label="say(copy.customer)">{{entry.customer_name||'—'}}</td><td class="finance-items" :data-label="say(entry.kind==='expense'?copy.shopping:entry.category==='experience'?copy.session:copy.purchased)"><ul><li v-for="(item,i) in entry.items" :key="i">{{item}}</li></ul><small v-if="entry.reservation_id">{{say(copy.source)}} · {{entry.reservation_id}}</small></td><td :data-label="say(copy.category)">{{categoryText(entry.category)}}</td><td class="finance-amount" :data-label="say(copy.amount)"><span :class="{'is-pending':entry.needs_amount}">{{entry.needs_amount?say(copy.pending):money(entry.amount_cents,entry.currency)}}</span><small v-if="entry.currency==='CNY'&&!entry.needs_amount" class="finance-converted">{{say(copy.converted).replace('{amount}',money(entry.cad_amount_cents))}}</small></td><td :data-label="say(copy.payment)">{{paymentLabel(entry.payment_method)}}</td><td class="finance-edit-cell"><button class="desk-link" @click="edit(entry)"><PhPencilSimple/>{{say(copy.edit)}}</button></td></tr></tbody></table><p v-else class="finance-empty">{{say(copy.empty)}}</p></div>
  <footer class="finance-pagination"><button class="desk-link" :disabled="page<=1||busy" @click="page--;load()">{{say(copy.previous)}}</button><span>{{say(copy.page).replace('{page}',String(page)).replace('{total}',String(data?.total||0))}}</span><button class="desk-link" :disabled="page*40>=(data?.total||0)||busy" @click="page++;load()">{{say(copy.next)}}</button></footer>
  <SlideOver v-model="open" :title="say(selected?copy.edit:draft.kind==='expense'?copy.add_expense:copy.add_income)" :busy="saving"><form class="finance-form" @submit.prevent="save">
   <p v-if="selected?.source==='reservation'" class="finance-help">{{say(copy.source_note)}}</p>
   <div class="finance-form-pair"><label>{{say(copy.date)}}<input v-model="draft.occurred_on" type="date" required/></label><label>{{say(copy.amount)}} ({{currencyLabel(draft.currency)}})<input v-model="amount" inputmode="decimal" :placeholder="selected?.needs_amount?say(copy.pending):'0.00'" :required="selected?.source!=='reservation'"/></label></div>
   <label>{{say(copy.income)}} / {{say(copy.expense)}}<select v-model="draft.kind" @change="kindChanged"><option value="income">{{say(copy.income)}}</option><option value="expense">{{say(copy.expense)}}</option></select></label>
   <template v-if="draft.kind==='income'"><label>{{say(copy.category)}}<select v-model="draft.category"><option v-for="c in categories" :key="c.id" :value="c.id">{{locale==='zh'?c.zh:c.en}}</option></select></label><label>{{say(copy.customer)}}<input v-model="draft.customer_name" maxlength="120" autocomplete="off"/></label></template>
   <label v-if="draft.kind==='expense'">{{say(copy.currency)}}<select v-model="draft.currency" :aria-label="say(copy.currency)"><option value="CAD">CAD</option><option value="CNY">RMB</option></select></label><fieldset><legend>{{say(draft.kind==='expense'?copy.shopping:draft.category==='experience'?copy.session:copy.purchased)}}</legend><div v-for="(_,i) in draft.items" :key="i" class="finance-item-input"><input v-model="draft.items[i]" :aria-label="say(copy.item)+' '+(i+1)" maxlength="200" required/><button type="button" class="desk-link" :disabled="draft.items.length===1" :aria-label="say(copy.remove_item)" @click="draft.items.splice(i,1)"><PhTrash/></button></div><button class="desk-link" type="button" :disabled="draft.items.length>=50" @click="draft.items.push('')"><PhPlus/>{{say(copy.add_item)}}</button></fieldset>
   <label v-if="draft.kind==='income'">{{say(copy.payment)}}<select v-model="draft.payment_method" :aria-label="say(copy.payment)" @change="paymentChanged"><option v-if="!payments.some(p=>p===draft.payment_method)" :value="draft.payment_method">{{paymentLabel(draft.payment_method)}}</option><option v-for="method in payments" :key="method" :value="method">{{label(method)}}</option></select></label><label>{{say(copy.note)}}<textarea v-model="draft.note" rows="2" maxlength="1000"/></label>
   <div v-if="draft.currency==='CNY'" class="finance-fx"><p v-if="fxBusy" class="finance-help">{{say(copy.fx_loading)}}</p><p v-else-if="quote" class="finance-help">{{say(copy.fx_rate).replace('{rate}',quote.rate).replace('{date}',quote.rate_date)}}<br/>{{say(copy.fx_note)}}</p><p v-if="fxError" class="desk-error" role="alert">{{fxError}} <button type="button" class="desk-link" @click="loadQuote">{{say(copy.refresh)}}</button></p></div><p v-if="editError" class="desk-error" role="alert">{{editError}}</p><div class="finance-form-actions"><button class="desk-button" type="submit" :disabled="saving||fxBusy||!!fxError">{{say(saving?copy.saving:copy.save)}}</button><button type="button" class="desk-link" :disabled="saving" @click="open=false">{{say(copy.cancel)}}</button></div>
   <details v-if="history.length"><summary>{{say(copy.history)}} · {{history.length}}</summary><ul class="finance-history"><li v-for="h in history" :key="h.id"><span>{{new Date(h.created_at*1000).toLocaleString(locale==='zh'?'zh-CN':'en-CA',{timeZone:'America/Toronto'})}}</span><span>{{h.snapshot.occurred_on}} · {{h.snapshot.customer_name}} · {{money(h.snapshot.amount_cents,h.snapshot.currency)}}</span></li></ul></details>
   <button v-if="selected&&!voiding" type="button" class="desk-link finance-void" @click="voiding=true">{{say(copy.void)}}</button><div v-if="voiding" class="finance-void-form"><p>{{say(copy.void_confirm)}}</p><input v-model="reason" :placeholder="say(copy.void_reason)" maxlength="500"/><button class="desk-button" type="button" :disabled="saving||!reason.trim()" @click="remove">{{say(copy.void)}}</button></div>
  </form></SlideOver>
  <SlideOver v-model="categoryOpen" :title="say(copy.new_category)" :busy="saving"><form class="finance-form" @submit.prevent="addCategory"><label>{{say(copy.category_zh)}}<input v-model="categoryName.zh" maxlength="40" required/></label><label>{{say(copy.category_en)}}<input v-model="categoryName.en" maxlength="60" required/></label><p v-if="editError" class="desk-error">{{editError}}</p><button class="desk-button" :disabled="saving">{{say(copy.save)}}</button></form></SlideOver>
 </section>
</template>
<style scoped>
.finance-panel{min-width:0}.finance-heading{display:flex;align-items:center;justify-content:space-between;gap:16px;margin:16px 0 24px}.finance-heading h1{font-size:30px;margin:0}.finance-heading>div,.finance-tools{display:flex;align-items:center;gap:14px}.finance-heading button,.finance-form button,.finance-edit-cell button{display:inline-flex;align-items:center;justify-content:center;gap:6px}.finance-totals{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}.finance-totals>div{background:#f0f6fa;padding:20px 24px;border:1px solid #dfe7ed;border-radius:16px;display:grid;gap:10px}.finance-totals span{color:#74828a;font-size:13px}.finance-totals strong{font-size:clamp(18px,2vw,27px);font-weight:500;overflow-wrap:anywhere}.finance-help{font-size:13px;color:#78858b;line-height:1.7}.finance-filters{display:grid;grid-template-columns:repeat(4,minmax(120px,1fr)) minmax(150px,1.4fr);gap:12px;align-items:end;margin:22px 0 12px}.finance-filters label,.finance-form label{display:grid;gap:8px;font-size:13px;color:#66757d}.finance-filters input,.finance-filters select,.finance-form input,.finance-form select,.finance-form textarea{width:100%;min-width:0;min-height:44px;border:1px solid #dce4e8;border-radius:9px;padding:10px 12px;background:white;color:#26343d;font:inherit;font-size:16px;box-sizing:border-box}.finance-tools{justify-content:space-between;font-size:13px;margin-bottom:16px}.finance-tools label{display:flex;gap:8px;align-items:center}.finance-records{border:1px solid #e0e7eb;border-radius:14px;background:white;overflow:hidden}.finance-records table{width:100%;border-collapse:collapse;font-size:13px;table-layout:fixed}.finance-records th{text-align:left;background:#f6f9fb;font-weight:500;color:#72818a;padding:14px 12px}.finance-records td{padding:16px 12px;border-top:1px solid #e5ebef;vertical-align:top;overflow-wrap:anywhere}.finance-records th:nth-child(3){width:23%}.finance-records th:last-child{width:92px}.finance-items ul{margin:0;padding-left:16px;line-height:1.7}.finance-items small{display:block;margin-top:6px;font-size:10px;color:#8a959b}.finance-amount{font-weight:600}.finance-converted{display:block;margin-top:6px;color:#7a858a;font-size:11px;font-weight:400}.finance-fx{padding:0 2px}.finance-fx p{margin:0}.is-pending{font-size:12px;color:#98734a;background:#faf2e7;padding:3px 7px;border-radius:6px;white-space:nowrap}.finance-empty{padding:44px 20px;text-align:center;color:#829097}.finance-pagination{display:flex;justify-content:space-between;align-items:center;gap:12px;margin:20px 0;font-size:13px}.finance-form{display:grid;gap:18px}.finance-form-pair{display:grid;grid-template-columns:1fr 1fr;gap:12px}.finance-form fieldset{border:0;padding:0;margin:0;min-width:0}.finance-form legend{font-size:13px;color:#66757d;margin-bottom:10px}.finance-item-input{display:flex;gap:8px;margin-bottom:8px}.finance-item-input button{flex-shrink:0;min-width:44px;min-height:44px}.finance-form-actions{display:flex;gap:16px;position:sticky;bottom:0;padding:12px 0;background:#fff;z-index:1}.finance-history{list-style:none;padding:0;font-size:12px;color:#7a858a}.finance-history li{display:grid;gap:5px;padding:12px 0;border-bottom:1px solid #eee}.finance-void{justify-self:start;color:#996459}.finance-void-form{display:grid;gap:12px;background:#fcf4f0;border-radius:12px;padding:16px;font-size:13px}.finance-form summary{cursor:pointer;font-size:13px}
@media(max-width:1050px){.finance-filters{grid-template-columns:repeat(2,minmax(0,1fr))}.finance-filters>input{grid-column:1/-1}.finance-records table{font-size:12px}.finance-records td,.finance-records th{padding:12px 8px}}
@media(max-width:700px){.finance-heading{align-items:flex-start;flex-direction:column;gap:12px;margin-top:8px}.finance-heading h1{font-size:27px}.finance-heading>div{width:100%;gap:8px;flex-wrap:wrap}.finance-heading .desk-button{padding:10px 13px}.finance-totals{gap:8px}.finance-totals>div{padding:14px 10px;border-radius:12px;gap:8px}.finance-totals strong{font-size:16px}.finance-totals span{font-size:11px}.finance-records table,.finance-records tbody{display:block}.finance-records thead{display:none}.finance-records tr{display:grid;grid-template-columns:1fr 1fr;padding:12px;gap:12px;border-top:1px solid #e5ebef}.finance-records tr:first-child{border-top:0}.finance-records td{display:block;border:0;padding:0;min-width:0}.finance-records td::before{content:attr(data-label);display:block;font-size:11px;color:#89939a;margin-bottom:5px}.finance-records .finance-items{grid-column:1/-1;grid-row:2}.finance-edit-cell{grid-column:1/-1;text-align:right}.finance-pagination{font-size:12px}.finance-form-pair{gap:10px}.finance-help{font-size:12px}}
</style>
