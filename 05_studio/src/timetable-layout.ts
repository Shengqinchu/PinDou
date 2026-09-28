export type TimetableBooking={patch_gift_guests?:number;plan?:'hourly'|'day'|'patch';id:string;date:string;start:string;end:string;name:string;note:string;guests:number;status:'pending'|'confirmed'|'completed'};
export type PlacedBooking=TimetableBooking&{lane:number;columns:number};
// Connected overlap groups share columns; adjacent bookings can reuse a lane.
export function layoutBookings(bookings:TimetableBooking[]):PlacedBooking[]{
 const ordered=[...bookings].sort((a,b)=>a.start.localeCompare(b.start)||b.end.localeCompare(a.end)||a.id.localeCompare(b.id));
 const result:PlacedBooking[]=[];let cluster:TimetableBooking[]=[],end='';
 function flush(){
  const lanes:string[]=[],placed:PlacedBooking[]=[];
  for(const booking of cluster){let lane=lanes.findIndex(until=>until<=booking.start);if(lane<0)lane=lanes.length;lanes[lane]=booking.end;placed.push({...booking,lane,columns:0});}
  for(const booking of placed)result.push({...booking,columns:lanes.length});
  cluster=[];
 }
 for(const booking of ordered){if(cluster.length&&booking.start>=end)flush();cluster.push(booking);end=cluster.length===1?booking.end:booking.end>end?booking.end:end;}
 flush();return result;
}
