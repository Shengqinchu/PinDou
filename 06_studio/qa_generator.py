"""Isolated Studio database + synthetic generator API. Bound only to loopback."""
from pathlib import Path
import sys,json,time,uuid,asyncio
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'06_studio'))
import qa_server as qa
from auth_fixture import fake_upstream,profiles
from fastapi import Request,HTTPException
from fastapi.responses import FileResponse,JSONResponse
import uvicorn
app=qa.studio.app
# /api/v1 is a separate origin service in production; do not apply Studio's small-form limit to the synthetic generator.
for middleware in app.user_middleware:
 dispatch=middleware.kwargs.get('dispatch')
 if getattr(dispatch,'__name__','')=='response_controls':
  async def controls_for_studio(request,call_next,original=dispatch):
   if request.url.path.startswith('/api/v1/'):return await call_next(request)
   return await original(request,call_next)
  middleware.kwargs['dispatch']=controls_for_studio
requests=[];artworks={};jobs={};delay=0.;fail_save=False;fail_generate=False;tutorial=False
palette=[{'brand':'MARD','code':'A1','name_cn':'Light Beige','hex':'#FAF5CD','rgb':[250,245,205]},
 {'brand':'MARD','code':'B1','name_cn':'Blue','hex':'#2D79C7','rgb':[45,121,199]}]
def image_path():return root/('artifacts/generator-integration/tutorial-pattern.png' if tutorial else '01_research/tech/test_inputs/cartoon_synthetic.png')
def pattern(width=26,height=26):
 if tutorial:
  p=json.loads((root/'artifacts/generator-integration/tutorial-pattern.json').read_text(encoding='utf-8'));p.update(image_url='/qa/pattern.png');p['metadata']={'labeled_image_url':'/qa/pattern.png'};return p
 grid=[[palette[(r+c)%2] for c in range(width)] for r in range(height)]
 return {'grid':grid,'palette_used':palette,'color_counts':{'A1':(width*height+1)//2,'B1':width*height//2},'bead_total':width*height,'image_url':'/qa/pattern.png','metadata':{'labeled_image_url':'/qa/pattern.png'}}
def current(request):
 token=request.headers.get('authorization','').removeprefix('Bearer ')
 if not token:return {'user_id':'qa-guest','nickname':'Guest','is_anonymous':True}
 return fake_upstream('profile',None,token=token)
def artwork(owner,ident='qa-pattern',width=26,height=26):
 return {'artwork_id':ident,'title':'QA pattern','size_preset':f'{width}x{height}','style_preset':'cartoon_fallback','owner_id':owner,'pattern_data':pattern(width,height),'preview_url':'/qa/pattern.png','thumbnail_url':'/qa/pattern.png','created_at':'2026-09-09T10:00:00Z'}
@app.get('/qa/pattern.png')
def png():return FileResponse(image_path())
@app.api_route('/api/v1/{path:path}',methods=['GET','POST','PUT','PATCH','DELETE'])
async def api(path:str,request:Request):
 global delay,fail_generate,fail_save
 if path=='admin/login':return {'token':'qa-admin','access_token':'qa-admin','token_type':'bearer'}
 user=current(request);owner=user['user_id']
 def profile():return user|{'paid_credits':512,'ai_points_balance':512,'ai_generation_cost_points':128,'normal_trial_remaining':3,'free_credits_remaining':3,'membership_expires_at':None,'created_at':'2026-09-09T10:00:00Z'}
 if request.method!='GET':requests.append({'path':path,'method':request.method,'owner':owner})
 if path in ('user/profile','wallet/profile'):return profile()
 if path=='user/consent':return {'success':True}
 if path=='payment/skus':return {'ai_generation_cost_points':128,'items':[{'sku_id':'points_standard_990','sku':'points_standard_990','category':'points','title':'标准包','amount_cny':'9.90','points':1024,'active':True},{'sku_id':'membership_month_1990','sku':'membership_month_1990','category':'membership','title':'月卡','amount_cny':'19.90','days':30,'gift_points':188,'active':True}]}
 if path=='cdk/redeem':return {'success':True,'message':'积分兑换成功，余额已刷新。','value':188,'owner_id':owner}
 if path in ('generate/script','generate/ai'):
  form=await request.form();w,h=map(int,str(form.get('size','26x26')).split('x'));requests[-1].update(mode=form.get('mode','ai'),size=f'{w}x{h}')
  if delay:await asyncio.sleep(delay)
  if fail_generate:return JSONResponse({'error':'AI_QUOTA_EXCEEDED','message_cn':'AI 积分不足'},status_code=403)
  a=artwork(owner,'qa-'+uuid.uuid4().hex[:8],w,h);artworks[a['artwork_id']]=a
  result={'artwork_id':a['artwork_id'],'pattern':a['pattern_data'],'pattern_url':'/qa/pattern.png'}
  if path=='generate/ai':
   ident='job-'+uuid.uuid4().hex[:6];jobs[ident]={'job_id':ident,'status':'succeeded','mode':'ai','stage':'completed','progress':100,'message_cn':'图纸已生成','result':result};return jobs[ident]|{'status':'queued','progress':1,'stage':'queued'}
  return result
 if path.startswith('generate/status/'):return jobs[path.split('/')[-1]]
 if path=='artwork/gallery':
  page=int(request.query_params.get('page',1));size=int(request.query_params.get('size',8));own=[a for a in artworks.values() if a['owner_id']==owner]
  return {'items':[a|{'bead_count':a['pattern_data']['bead_total'],'color_count':len(a['pattern_data']['palette_used'])} for a in own[(page-1)*size:page*size]],'page':page,'size':size,'total':len(own),'has_more':len(own)>page*size}
 if path.startswith('artwork/'):
  ident=path.split('/')[1]
  if ident=='qa-pattern' and ident not in artworks:artworks[ident]=artwork(owner)
  a=artworks.get(ident)
  if not a or a['owner_id']!=owner:raise HTTPException(404,'not_found')
  if path.endswith('/pattern') and request.method=='PUT':
   if fail_save:return JSONResponse({'error':'SAVE_FAILED','message_cn':'保存失败，请稍后再试。'},status_code=503)
   data=await request.json();a['pattern_data']=data['pattern_json']|{'image_url':'/qa/pattern.png','metadata':{'labeled_image_url':'/qa/pattern.png'}}
   return {'success':True,'pattern':a['pattern_data'],'artwork':a,'pattern_url':'/qa/pattern.png'}
  return a
 return {}
@app.post('/qa/controls')
async def controls(request:Request):
 global delay,fail_save,fail_generate,tutorial
 data=await request.json();tutorial=bool(data.get('tutorial',False));delay=float(data.get('delay',0));fail_save=bool(data.get('fail_save',False));fail_generate=bool(data.get('fail_generate',False))
 if data.get('clear'):requests.clear();artworks.clear();jobs.clear()
 return {'ok':True}
@app.get('/qa/requests')
def log():return requests
@app.get('/{path:path}')
def site(path:str):
 base=root/'05_studio/dist';file=(base/path).resolve()
 if file.is_relative_to(base.resolve()) and file.is_file():return FileResponse(file)
 return FileResponse(base/'index.html',headers={'Cache-Control':'no-store'})
@app.post('/qa/timetable-seed')
def seed():
 import reservations as r
 stamp=r.now_local().isoformat();date=stamp[:10]
 with qa.studio.database() as db:
  for i,status in enumerate(['confirmed','pending','completed','cancelled']):
   payload={'name':'Timetable QA '+str(i),'contact_method':'wechat','contact':'local-qa','booking':{'date':date,'start':'14:00','end':'16:00','plan':'hourly','guests':i+1}}
   ident='VIS-TABLE-'+uuid.uuid4().hex[:8]
   db.execute('INSERT INTO studio_reservations(id,created_at,updated_at,status,payload,visitor_hash,idempotency_key,payload_hash,owner_id) VALUES(?,?,?,?,?,?,?,?,?)',(ident,stamp,stamp,status,json.dumps(payload),'qa',str(uuid.uuid4()),'qa','qa-owner'))
 return {'date':date}
uvicorn.run(app,host='127.0.0.1',port=19678,access_log=False)
