"""Upload a verified release package in hashed chunks; does not deploy."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
from dotenv import dotenv_values
import paramiko,json,hashlib,io,re
root=Path(__file__).resolve().parents[1]
meta=json.loads((root/'artifacts/studio-release/latest.json').read_text())
version=meta['version'];assert re.fullmatch(r'\d{14}-studio-v[67]',version)
data=Path(meta['archive']).read_bytes();assert hashlib.sha256(data).hexdigest()==meta['sha256']
cfg=dotenv_values(root/'.env')
def connect():
 c=paramiko.SSHClient();c.set_missing_host_key_policy(paramiko.AutoAddPolicy());c.connect(cfg['PINDOU_PROD_SSH_HOST'],username='root',key_filename=cfg['PINDOU_PROD_SSH_KEY_PATH'],timeout=25);return c
parts=[data[i:i+3*1024*1024] for i in range(0,len(data),3*1024*1024)]
def upload(index):
 c=connect()
 try:
  path=f'/tmp/{version}.part-{index:02d}';payload=parts[index];s=c.open_sftp();s.putfo(io.BytesIO(payload),path,file_size=len(payload),confirm=True);s.chmod(path,0o600);s.close()
  _,out,err=c.exec_command('sha256sum '+path,timeout=30);digest=out.read().decode().split()[0]
  assert digest==hashlib.sha256(payload).hexdigest()
  print(json.dumps({'part':index+1,'of':len(parts),'bytes':len(payload),'verified':True}),flush=True)
 finally:c.close()
with ThreadPoolExecutor(max_workers=4) as pool:
 for result in as_completed([pool.submit(upload,i) for i in range(len(parts))]):result.result()
c=connect()
try:
 s=c.open_sftp()
 for source,target in [('studio_deploy.py','studio_deploy_v7.py'),('studio_assemble_upload.py','studio_assemble_v7.py')]:
  s.put(str(root/'07_ops'/source),'/tmp/'+target);s.chmod('/tmp/'+target,0o600)
 s.close()
 _,out,err=c.exec_command(f"python3 /tmp/studio_assemble_v7.py {version} {len(parts)} {meta['sha256']}",timeout=45)
 result=out.read().decode();error=err.read().decode();assert out.channel.recv_exit_status()==0,error
 print(result,flush=True)
 (root/'artifacts/studio-release/upload.json').write_text(json.dumps(meta|{'parts':len(parts),'bytes':len(data),'assembled':True},indent=2))
finally:c.close()
