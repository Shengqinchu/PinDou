import assert from 'node:assert/strict';
import {layoutBookings} from '../src/timetable-layout.ts';
const booking=(id,start,end)=>({id,start,end,date:'2026-09-11',name:id,note:'',guests:2,status:'confirmed'});
const touching=layoutBookings([booking('a','10:00','12:00'),booking('b','12:00','14:00')]);
assert(touching.every(x=>x.lane===0&&x.columns===1));
const chain=layoutBookings([booking('a','10:00','13:00'),booking('b','12:00','15:00'),booking('c','14:00','16:00')]);
assert(chain.every(x=>x.columns===2));assert.equal(chain[0].lane,chain[2].lane);
for(let count=1;count<=32;count++){
 const source=Array.from({length:count},(_,i)=>booking(String(i).padStart(3,'0'),`${String(10+(i%4)).padStart(2,'0')}:00`,`${String(16+(i%3)).padStart(2,'0')}:00`));
 const result=layoutBookings(source);assert.deepEqual(result,layoutBookings(source.toReversed()));
 assert.equal(result.length,source.length);
 for(let i=0;i<result.length;i++)for(let j=i+1;j<result.length;j++){
  const a=result[i],b=result[j];if(a.start<b.end&&b.start<a.end)assert.notEqual(a.lane,b.lane);
 }
 assert(result.every(x=>x.lane<x.columns));
}
console.log('Timetable layout: adjacent, chained, stable order and 1–32 overlapping groups passed.');
