"""Explicit public HTTPS document import; pinned DNS, no credentials or private network access."""
import hashlib, http.client, ipaddress, re, socket, ssl, time
from html.parser import HTMLParser
from urllib.parse import urlsplit, urljoin, quote
from fastapi import Depends
from app import app, ident, require, bounded, limit, fail
from store import *
import ai

MAX_BYTES=1_000_000
REDIRECTS={301,302,303,307,308}

def validate_url(url):
    p=urlsplit(url)
    host=p.hostname or ''
    try:port=p.port
    except ValueError:raise ValueError('잘못된 포트')
    if p.scheme!='https' or p.username or p.password or port not in (None,443) or not host or len(host)>253 or '.' not in host or any(ch.isspace() for ch in url):
        raise ValueError('공개 HTTPS 웹페이지(443 포트)만 지원합니다.')
    host=host.encode('idna').decode('ascii').lower()
    if not re.fullmatch(r'[a-z0-9.-]+',host):raise ValueError('도메인 형식 오류')
    try:ipaddress.ip_address(host)
    except ValueError:pass
    else:raise ValueError('IP 주소 직접 입력 금지')
    return p,host

def resolve_public(host):
    ips=list(dict.fromkeys(r[4][0] for r in socket.getaddrinfo(host,443,type=socket.SOCK_STREAM)))
    if not ips:raise ValueError('도메인 조회 실패')
    for ip in ips:
        v=ipaddress.ip_address(ip)
        if not v.is_global or v.is_multicast or v.is_reserved or getattr(v,'ipv4_mapped',None):raise ValueError('사설·예약 네트워크 주소 접근 금지')
    return ips

class PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self,host,ip):
        super().__init__(host,443,timeout=8,context=ssl.create_default_context());self.ip=ip
    def connect(self):
        raw=socket.create_connection((self.ip,443),self.timeout)
        try:self.sock=self._context.wrap_socket(raw,server_hostname=self.host)
        except BaseException:raw.close();raise

class PlainHTML(HTMLParser):
    def __init__(self):super().__init__(convert_charrefs=True);self.skip=0;self.parts=[]
    def handle_starttag(self,tag,attrs):
        if tag in {'script','style','noscript','svg','template'}:self.skip+=1
        elif not self.skip and tag in {'p','div','section','article','li','br','tr','h1','h2','h3','h4'}:self.parts.append('\n')
    def handle_endtag(self,tag):
        if tag in {'script','style','noscript','svg','template'}:self.skip=max(0,self.skip-1)
        elif not self.skip and tag in {'p','div','section','article','li','tr'}:self.parts.append('\n')
    def handle_data(self,data):
        if not self.skip:self.parts.append(data)

def fetch_text(url):
    deadline=time.monotonic()+25
    for hop in range(4):
        if time.monotonic()>deadline:raise ValueError('웹페이지 수집 시간 초과')
        p,host=validate_url(url);ips=resolve_public(host);conn=PinnedHTTPS(host,ips[0])
        target=quote(p.path or '/',safe="/%:@!$&'()*+,;=-._~")
        if p.query:target+='?'+quote(p.query,safe="/%?:@!$&'()*+,;=-._~")
        try:
            conn.request('GET',target,headers={'Accept':'text/html,text/plain','Accept-Encoding':'identity','User-Agent':'CSAI-DocumentImport/1.0','Connection':'close'})
            r=conn.getresponse()
            if r.status in REDIRECTS:
                dest=r.getheader('Location')
                if not dest or hop==3:raise ValueError('리디렉션 제한')
                url=urljoin(url,dest);continue
            if r.status!=200:raise ValueError('웹페이지 응답 실패: '+str(r.status))
            typ=r.getheader('Content-Type','').lower()
            if typ.split(';')[0].strip() not in {'text/html','text/plain','application/xhtml+xml'}:raise ValueError('HTML 또는 일반 텍스트만 지원합니다.')
            if r.getheader('Content-Encoding','identity').lower()!='identity':raise ValueError('압축 응답은 지원하지 않습니다.')
            size=r.getheader('Content-Length')
            if size and int(size)>MAX_BYTES:raise ValueError('웹페이지 최대 1MB')
            chunks=[];n=0
            while True:
                if time.monotonic()>deadline:raise ValueError('웹페이지 수집 시간 초과')
                b=r.read1(min(65536,MAX_BYTES+1-n))
                if not b:break
                n+=len(b)
                if n>MAX_BYTES:raise ValueError('웹페이지 최대 1MB')
                chunks.append(b)
            charset=re.search(r'charset\s*=\s*["\']?([\w-]+)',typ)
            encoding=charset.group(1) if charset else 'utf-8'
            if encoding not in {'utf-8','utf8','euc-kr','cp949','us-ascii','iso-8859-1'}:encoding='utf-8'
            text=b''.join(chunks).decode(encoding,errors='replace')
            if typ.startswith('text/html') or typ.startswith('application/xhtml+xml'):
                parser=PlainHTML();parser.feed(text);text=''.join(parser.parts)
            text=ai.clean(re.sub(r'[ \t]+',' ',text).strip())
            if not text or len(text)>60000:raise ValueError('본문이 없거나 60,000자 초과입니다. 자료를 나누어 등록하세요.')
            return text,host
        finally:conn.close()
    raise ValueError('리디렉션 제한')

@app.post('/api/files/url')
def url_import(body:dict,ws=Depends(ident)):
    limit('url_import:'+ws,5,300)
    url=bounded(body.get('url',''),2000)
    try:text,host=fetch_text(url)
    except (ValueError,OSError,http.client.HTTPException,UnicodeError) as exc:fail(422,'웹페이지 수집 실패: '+str(exc)[:150])
    sha=hashlib.sha256(text.encode()).hexdigest()
    with db(True) as c:
        from branding import owned_agent
        agent=body.get('agent','');owned_agent(c,getw(c,ws),agent)
        if agent:sha=hashlib.sha256((agent+':'+sha).encode()).hexdigest()
        old=one(c,'SELECT id FROM file WHERE ws=? AND sha=?',(ws,sha))
        if old:return {'id':old['id'],'duplicate':True}
        require(one(c,'SELECT count(*) n FROM file WHERE ws=?',(ws,))['n']<50,'파일 최대 50개',422)
        i=uid();c.execute('INSERT INTO file VALUES(?,?,?,?,?,?,?)',(i,ws,'웹페이지: '+host,sha,text,'[]',now()))
        if agent:c.execute('INSERT INTO file_brand VALUES(?,?,?)',(i,ws,agent))
    return {'id':i,'chars':len(text),'estimate':ai.estimate(text,[])}
