export type FinanceCategory={id:string;zh:string;en:string};
export type FinanceEntry={id:string;kind:'income'|'expense';category:string;occurred_on:string;customer_name:string;items:string[];amount_cents:number|null;payment_method:string;note:string;reservation_id:string|null;source:string;version:number;created_at:number;updated_at:number;needs_amount:boolean};
export type FinanceSummary={income_cents:number;expense_cents:number;balance_cents:number;needs_amount:number;categories:{category:string;amount_cents:number}[]};
export type FinancePage={items:FinanceEntry[];total:number;page:number;start:string;end:string;summary:FinanceSummary;categories:FinanceCategory[]};
export type FinanceDraft=Pick<FinanceEntry,'kind'|'category'|'occurred_on'|'customer_name'|'items'|'amount_cents'|'payment_method'|'note'>;
export function centsFromInput(value:string):number|null{
  if(!/^\d{1,7}(?:\.\d{1,2})?$/.test(value.trim()))return null;
  const [whole,fraction='']=value.trim().split('.');const amount=Number(whole)*100+Number(fraction.padEnd(2,'0'));
  return Number.isSafeInteger(amount)&&amount<=100000000?amount:null;
}
export function money(cents:number|null){return cents===null?'—':(cents/100).toLocaleString('en-CA',{minimumFractionDigits:2,maximumFractionDigits:2})+' CAD';}
