import businessCopy from './content/business.json';
export type FinanceCurrency='CAD'|'CNY';
export type FinanceQuote={rate:string;rate_date:string;source:string};
export type FinanceCategory={id:string;zh:string;en:string};
export type FinanceEntry={id:string;kind:'income'|'expense';category:string;occurred_on:string;customer_name:string;items:string[];amount_cents:number|null;currency:FinanceCurrency;cad_amount_cents:number|null;fx_rate:string|null;fx_date:string|null;fx_source:string;payment_method:string;note:string;reservation_id:string|null;source:string;version:number;created_at:number;updated_at:number;needs_amount:boolean};
export type FinanceSummary={income_cents:number;expense_cents:number;balance_cents:number;needs_amount:number;categories:{category:string;amount_cents:number}[]};
export type FinancePage={items:FinanceEntry[];total:number;page:number;start:string;end:string;summary:FinanceSummary;categories:FinanceCategory[]};
export type FinanceDraft=Pick<FinanceEntry,'kind'|'category'|'occurred_on'|'customer_name'|'items'|'amount_cents'|'currency'|'payment_method'|'note'>;
export const financePayments=['cash','transfer','wechat_alipay','stored'] as const;
export function paymentKey(value:string){
 const lower=value.toLowerCase();
 for(const key of financePayments)if([key,...businessCopy[key].map(s=>s.toLowerCase())].includes(lower))return key;
 if([...businessCopy.transfer_legacy.map(s=>s.toLowerCase()),'e-transfer'].includes(lower))return 'transfer';
 return value;
}
export function paymentCurrency(method:string):FinanceCurrency{return paymentKey(method)==='wechat_alipay'?'CNY':'CAD';}
export function currencyLabel(currency:FinanceCurrency='CAD'){return currency==='CNY'?'RMB':'CAD';}
export function centsFromInput(value:string):number|null{
  if(!/^\d{1,7}(?:\.\d{1,2})?$/.test(value.trim()))return null;
  const [whole,fraction='']=value.trim().split('.');const amount=Number(whole)*100+Number(fraction.padEnd(2,'0'));
  return Number.isSafeInteger(amount)&&amount<=100000000?amount:null;
}
export function money(cents:number|null,currency:FinanceCurrency='CAD'){return cents===null?'—':(cents/100).toLocaleString('en-CA',{minimumFractionDigits:2,maximumFractionDigits:2})+' '+currencyLabel(currency);}
