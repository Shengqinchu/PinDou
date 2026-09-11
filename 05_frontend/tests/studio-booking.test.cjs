const {test}=require('node:test');
const assert=require('node:assert/strict');
const {validBooking,chooseCell,validContact,requestId,retryUnchanged}=require('../src/utils/studio-booking.ts');
const clock=m=>`${Math.floor(m/60)}`.padStart(2,'0')+':'+`${m%60}`.padStart(2,'0');
function schedule(close='22:00'){
 return {today:'2026-09-10',timezone:'America/Toronto',minimum_minutes:120,max_guests_per_group:6,policy_version:4,days:[{date:'2026-09-11',open:'10:00',close,closed:false,slots:Array.from({length:24},(_,i)=>({start:clock(600+i*30),end:clock(630+i*30),available:clock(600+i*30)<close,reason:null}))}]};
}
const booking=(changes={})=>({date:'2026-09-11',start:'20:00',end:'22:00',plan:'hourly',guests:2,...changes});
test('22:00 is an end boundary, while late starts still require two hours',()=>{
 const c=schedule();assert(validBooking(c,booking()));assert(!validBooking(c,booking({start:'21:00'})));assert(!validBooking(c,booking({end:'23:00'})));
});
test('day visits follow the selected day closing and the current group limit',()=>{
 const c=schedule('18:00');assert(validBooking(c,booking({start:'11:00',end:'18:00',plan:'day'})));assert(!validBooking(c,booking({start:'11:00',end:'17:30',plan:'day'})));assert(!validBooking(c,booking({start:'11:00',end:'18:00',guests:7})));
});
test('closed days, capacity blocks and missing intervals cannot be crossed',()=>{
 const c=schedule();c.days[0].slots[21].available=false;assert(!validBooking(c,booking()));c.days[0].slots[21].available=true;c.days[0].slots.splice(21,1);assert(!validBooking(c,booking()));c.days[0].closed=true;assert(!validBooking(c,booking({start:'10:00',end:'12:00'})));
});
test('the same grid chooses a start and a later end without a second date step',()=>{
 const c=schedule(),d=c.days[0];const first=chooseCell(c,booking({start:'',end:''}),d,d.slots[4],false);assert.deepEqual([first.booking.start,first.booking.end],['12:00','14:00']);
 const extended=chooseCell(c,first.booking,d,d.slots[11],true);assert.deepEqual([extended.booking.start,extended.booking.end],['12:00','16:00']);assert.equal(extended.choosingEnd,false);
 d.slots[8].available=false;assert.equal(chooseCell(c,first.booking,d,d.slots[11],true),null);
});
test('the calendar is authoritative for minimum duration',()=>{
 const c=schedule();c.minimum_minutes=180;const chosen=chooseCell(c,booking(),c.days[0],c.days[0].slots[0],false);assert.equal(chosen.booking.end,'13:00');assert(!validBooking(c,booking({start:'10:00',end:'12:00'})));
});
test('only eligible returning accounts may omit both contact fields',()=>{
 const empty={name:'',contact_method:'wechat',contact:''};assert(!validContact(empty));assert(validContact(empty,true));assert(!validContact({...empty,name:'Guest'},true));assert(!validContact({name:'Guest',contact_method:'email',contact:'bad-email'}));assert(validContact({name:'Guest',contact_method:'phone',contact:'+1 416 555 0123'}));
});
test('uncertain submission results retain the exact request; rejected edits can be reviewed',()=>{
 for(const status of [0,500,502,503])assert(retryUnchanged(status,''));assert(retryUnchanged(409,'reservation_session_missing'));assert(retryUnchanged(409,'reservation_request_changed'));assert(!retryUnchanged(409,'booking_profile_changed'));assert(!retryUnchanged(422,'reservation_interval_unavailable'));
 const ids=new Set(Array.from({length:300},()=>requestId()));assert.equal(ids.size,300);for(const id of ids)assert.match(id,/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
});
