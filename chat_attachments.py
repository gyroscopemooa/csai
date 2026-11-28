"""Small, private, re-encoded photo attachments; no AI image processing or public file URLs."""
import base64,io,re,binascii
from PIL import Image,ImageOps
from fastapi import Depends
from app import app,ident,require,bounded,visitor,limit
from store import *
import ops,branding,staff_access

MAX_UPLOAD=1_000_000
MAX_FILE=4_000_000
FILE_TYPES={'.pdf':'application/pdf','.txt':'text/plain','.mp4':'video/mp4','.webm':'video/webm'}
MAX_TOTAL=50_000_000
MAX_PER_THREAD=20

def init():
    with db(True) as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS chat_photo_setting(ws TEXT NOT NULL,agent TEXT NOT NULL,enabled INTEGER NOT NULL,PRIMARY KEY(ws,agent));
        CREATE TABLE IF NOT EXISTS chat_photo(id TEXT PRIMARY KEY,ws TEXT NOT NULL,thread TEXT NOT NULL REFERENCES thread(id) ON DELETE CASCADE,message TEXT NOT NULL UNIQUE REFERENCES message(id) ON DELETE CASCADE,sender TEXT NOT NULL,actor TEXT NOT NULL,client TEXT NOT NULL,data TEXT NOT NULL,bytes INTEGER NOT NULL,created INTEGER NOT NULL,UNIQUE(ws,thread,actor,client));
        CREATE INDEX IF NOT EXISTS chat_photo_scope ON chat_photo(ws,thread,created);
        """)
        for table,column,ddl in [('chat_photo_setting','files_enabled',"ALTER TABLE chat_photo_setting ADD COLUMN files_enabled INTEGER NOT NULL DEFAULT 0"),('chat_photo','mime',"ALTER TABLE chat_photo ADD COLUMN mime TEXT NOT NULL DEFAULT 'image/jpeg'"),('chat_photo','filename',"ALTER TABLE chat_photo ADD COLUMN filename TEXT NOT NULL DEFAULT 'photo.jpg'")]:
            if column not in [r[1] for r in c.execute("PRAGMA table_info("+table+")")]:c.execute(ddl)
init()

def enabled(c,ws,agent):
    x=one(c,'SELECT enabled FROM chat_photo_setting WHERE ws=? AND agent=?',(ws,agent))
    return bool(x and x['enabled'])

def files_enabled(c,ws,agent):
    x=one(c,'SELECT files_enabled FROM chat_photo_setting WHERE ws=? AND agent=?',(ws,agent))
    return bool(x and x['files_enabled'])

def public_files_enabled(c,w,agent):
    return public_access(w) and files_enabled(c,w['id'],agent['id'] if agent else '') and bool(agent['enabled'] if agent else w['enabled'])

def public_enabled(c,w,agent):
    return public_access(w) and enabled(c,w['id'],agent['id'] if agent else '') and bool(agent['enabled'] if agent else w['enabled'])

def normalize(value):
    require(isinstance(value,str) and len(value)<=1_333_340,'사진은 1MB 이하입니다.',422)
    try:
        raw=base64.b64decode(value,validate=True)
        if not 0<len(raw)<=MAX_UPLOAD:raise ValueError()
        with Image.open(io.BytesIO(raw)) as im:
            if im.format not in ('JPEG','PNG','WEBP') or im.width*im.height>20_000_000 or getattr(im,'n_frames',1)!=1:raise ValueError()
            im.load();im=ImageOps.exif_transpose(im);im.thumbnail((1600,1600))
            rgba=im.convert('RGBA');rgb=Image.new('RGB',rgba.size,'white');rgb.paste(rgba,mask=rgba.getchannel('A'))
            out=io.BytesIO();rgb.save(out,format='JPEG',quality=85,optimize=True);data=out.getvalue()
            if not 0<len(data)<=MAX_UPLOAD:raise ValueError()
    except (OSError,ValueError,TypeError,binascii.Error,Image.DecompressionBombError):require(False,'JPG·PNG·WebP 정지 사진만 업로드 가능합니다.',422)
    return base64.b64encode(data).decode('ascii'),len(data)

def normalize_file(value,name):
    require(isinstance(value,str) and len(value)<=5_333_340,'파일은 4MB 이하입니다.',422)
    name=bounded(name,150)
    require(re.fullmatch(r'[^/\\\x00-\x1f\x7f]+',name) and not name.startswith('.') and not name.endswith('.'),'파일 이름 오류',422)
    ext='.'+name.rsplit('.',1)[-1].lower() if '.' in name else ''
    require(ext in FILE_TYPES,'PDF·TXT·MP4·WebM만 지원합니다.',422)
    try:
        raw=base64.b64decode(value,validate=True)
        if not 0<len(raw)<=MAX_FILE:raise ValueError()
        if ext=='.pdf' and not (raw.startswith(b'%PDF-') and b'%%EOF' in raw[-2048:]):raise ValueError()
        if ext=='.txt':
            text=raw.decode('utf-8-sig')
            if any(ord(ch)<32 and ch not in '\t\r\n' for ch in text) or '\x00' in text:raise ValueError()
        if ext=='.mp4' and not (len(raw)>=16 and raw[4:8]==b'ftyp' and 8<=int.from_bytes(raw[:4],'big')<=len(raw)):raise ValueError()
        if ext=='.webm' and not (raw.startswith(bytes.fromhex('1a45dfa3')) and b'webm' in raw[:4096]):raise ValueError()
    except (ValueError,UnicodeError,binascii.Error):require(False,'지원 파일 형식과 내용이 일치하지 않습니다.',422)
    return base64.b64encode(raw).decode('ascii'),len(raw),FILE_TYPES[ext],name

def messages(c,ws,tid,cutoff=None,include_id=True):
    sql="SELECT m.id,m.role,m.body,m.created,p.id AS photo,p.mime AS file_mime,p.filename AS file_name FROM message m LEFT JOIN chat_photo p ON p.message=m.id AND p.ws=m.ws AND p.thread=m.thread WHERE m.ws=? AND m.thread=?"
    args=[ws,tid]
    if cutoff is not None:sql+=' AND m.created>=?';args.append(cutoff)
    out=[]
    for row in rows(c,sql+' ORDER BY m.rowid',args):
        photo=row.pop('photo',None)
        if not include_id:row.pop('id',None)
        mime=row.pop('file_mime',None);name=row.pop('file_name',None)
        if photo:
            if mime=='image/jpeg':row['photo']=photo
            else:row['attachment']={'id':photo,'mime':mime,'name':name}
        out.append(row)
    return out

def read(c,ws,tid,i,cutoff=None):
    sql='SELECT p.data,p.mime,p.filename FROM chat_photo p JOIN message m ON m.id=p.message AND m.ws=p.ws AND m.thread=p.thread WHERE p.ws=? AND p.thread=? AND p.id=?'
    args=[ws,tid,i]
    if cutoff is not None:sql+=' AND m.created>=?';args.append(cutoff)
    row=one(c,sql,args);require(row,'사진 없음 또는 조회 권한 없음',404)
    return {'mime':row['mime'],'data':row['data'],'name':row['filename']}

def save(c,w,tid,agent,role,actor,body):
    ws=w['id'];kind=body.get('kind','photo');require(kind in ('photo','file'),'첨부 유형 오류',422)
    require(public_access(w) and (enabled(c,ws,agent) if kind=='photo' else files_enabled(c,ws,agent)),'첨부 기능이 비활성화되어 있습니다.',403)
    client=bounded(body.get('client',''),100);require(re.fullmatch(r'[A-Za-z0-9_-]{12,100}',client),'요청 ID 오류',422)
    old=one(c,'SELECT id FROM chat_photo WHERE ws=? AND thread=? AND actor=? AND client=?',(ws,tid,actor,client))
    if old:return {'id':old['id'],'duplicate':True}
    require(not one(c,"SELECT client FROM request WHERE ws=? AND thread=? AND state='running'",(ws,tid)),'AI 응답 완료 후 첨부하세요.',409)
    require(one(c,'SELECT COUNT(*) n FROM chat_photo WHERE ws=? AND thread=?',(ws,tid))['n']<MAX_PER_THREAD,'상담당 첨부 최대 20개',409)
    used=one(c,'SELECT COALESCE(SUM(bytes),0) n FROM chat_photo WHERE ws=?',(ws,))['n']
    if kind=='photo':
        data,n=normalize(body.get('data'));mime,name='image/jpeg','photo.jpg'
    else:data,n,mime,name=normalize_file(body.get('data'),body.get('name',''))
    require(used+n<=MAX_TOTAL,'업체 첨부 저장 한도에 도달했습니다.',409)
    i,m=uid(),uid();c.execute('INSERT INTO message VALUES(?,?,?,?,?,?)',(m,ws,tid,role,'[사진 첨부 · 담당자 확인]' if kind=='photo' else '[파일 첨부 · 담당자 확인]',now()))
    c.execute('INSERT INTO chat_photo(id,ws,thread,message,sender,actor,client,data,bytes,created,mime,filename) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(i,ws,tid,m,role,actor,client,data,n,now(),mime,name))
    clear_temporary_takeover(c,ws,tid)
    if role=='user':
        c.execute("UPDATE thread SET manual=1,status='pending' WHERE ws=? AND id=?",(ws,tid))
        ops.event(c,ws,'handoff','고객 첨부 · 담당자 확인 필요',tid)
    else:c.execute("UPDATE thread SET manual=1,status='open' WHERE ws=? AND id=?",(ws,tid))
    return {'id':i,'duplicate':False}

@app.get('/api/chat-photos/settings')
def photo_settings(agent:str='',ws=Depends(ident)):
    with db() as c:
        ops.work_scope(c,getw(c,ws),agent)
        return {'enabled':enabled(c,ws,agent),'files_enabled':files_enabled(c,ws,agent)}

@app.post('/api/chat-photos/settings')
def photo_settings_save(body:dict,agent:str='',ws=Depends(ident)):
    require(type(body.get('enabled')) is bool and ('files_enabled' not in body or type(body['files_enabled']) is bool),'설정 오류',422)
    with db(True) as c:
        w=getw(c,ws);ops.work_scope(c,w,agent,True);require(public_access(w),'유료 상담 또는 체험 이용 권한 필요',403)
        c.execute('INSERT INTO chat_photo_setting(ws,agent,enabled,files_enabled) VALUES(?,?,?,?) ON CONFLICT(ws,agent) DO UPDATE SET enabled=excluded.enabled,files_enabled=excluded.files_enabled',(ws,agent,int(body['enabled']),int(body.get('files_enabled',files_enabled(c,ws,agent)))))
    return {'ok':True}

@app.post('/api/customer/photos')
def customer_upload(body:dict):
    token=bounded(body.get('token',''),100);limit('photo:'+token,5,60)
    with db(True) as c:
        v=visitor(c,token,kind='public');w=getw(c,v['ws']);agent=ops.public_work_scope(c,w,v)
        t=one(c,"SELECT id FROM thread WHERE ws=? AND visitor=? AND kind='public'",(v['ws'],token));require(t and ops.thread_brand(c,w,t['id'],True)==agent,'상담 없음',404)
        return save(c,w,t['id'],agent,'user','customer',body)

@app.post('/api/customer/photos/read')
def customer_read(body:dict):
    token=bounded(body.get('token',''),100);i=bounded(body.get('id',''),100);limit('photo-read:'+token,30,60)
    with db() as c:
        v=visitor(c,token,kind='public');t=one(c,"SELECT id FROM thread WHERE ws=? AND visitor=? AND kind='public'",(v['ws'],token));require(t,'상담 없음',404)
        return read(c,v['ws'],t['id'],i,history_cutoff(getw(c,v['ws'])))

@app.post('/api/inbox/{tid}/photos')
def owner_upload(tid:str,body:dict,ws=Depends(ident)):
    limit('photo-owner:'+ws,20,60)
    with db(True) as c:
        w=getw(c,ws);agent=ops.thread_brand(c,w,tid,True)
        require(one(c,"SELECT id FROM thread WHERE ws=? AND id=? AND kind='public'",(ws,tid)),'자체 웹 상담만 지원합니다.',409)
        return save(c,w,tid,agent,'staff','owner',body)

@app.get('/api/inbox/{tid}/photos/{i}')
def owner_read(tid:str,i:str,ws=Depends(ident)):
    with db() as c:
        w=getw(c,ws);ops.thread_brand(c,w,tid)
        return read(c,ws,tid,i,history_cutoff(w))

@app.post('/api/staff/{mid}/threads/{tid}/photos')
def employee_upload(mid:str,tid:str,body:dict,ws=Depends(ident)):
    limit('photo-staff:'+ws,20,60)
    with db(True) as c:
        m,w=staff_access.membership(c,ws,mid);t=staff_access.visible_thread(c,m,w,tid,True);require(t['kind']=='public','자체 웹 상담만 지원합니다.',409)
        return save(c,w,tid,m['agent'],'staff',mid,body)

@app.get('/api/staff/{mid}/threads/{tid}/photos/{i}')
def employee_read(mid:str,tid:str,i:str,ws=Depends(ident)):
    with db() as c:
        m,w=staff_access.membership(c,ws,mid);staff_access.visible_thread(c,m,w,tid)
        return read(c,m['ws'],tid,i,history_cutoff(w))
