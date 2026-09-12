import {test} from 'node:test';
import assert from 'node:assert/strict';
import {hoursInput,hoursNumber,minutesFromHours} from '../src/time-units.ts';

test('hours entered by the owner become exact API minutes',()=>{
 for(const [hours,minutes] of [['0.5',30],['1.5',90],['10',600],['24',1440],['0.25',15],['.5',30],['-0.5',-30],['0',0]])assert.equal(minutesFromHours(hours),minutes);
});
test('opening and saving legacy records preserves every existing minute',()=>{
 for(let minutes=1;minutes<=1440;minutes++)assert.equal(minutesFromHours(hoursInput(minutes)),minutes);
 assert.equal(hoursInput(null),'');assert.equal(hoursInput(90),'1.5');
});
test('invalid and sub-minute values do not silently round balances',()=>{
 for(const value of ['', ' ', 'abc', '0.001','1.01','0x10','1e3', Infinity,NaN,'9007199254740992'])assert.equal(minutesFromHours(value),null,String(value));
});
test('balances and signed history use hours',()=>{
 assert.equal(hoursNumber(90),'1.5');assert.equal(hoursNumber(-30),'-0.5');assert.equal(hoursNumber(0),'0');assert.equal(hoursNumber(600),'10');
});
