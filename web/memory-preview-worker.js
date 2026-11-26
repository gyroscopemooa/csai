'use strict';
// Local metadata only. Never uploads conversation contents.
const MAX_FILE=128*1024*1024,MAX_TOTAL=1024*1024*1024,MAX_FILES=20,MAX_COUNT=30000;
const groups={
 '사업·상품·서비스':['사업','상품','서비스','제품','고객','업체','창업','business','product','service'],
 '운영·업무 흐름':['업무','운영','예약','절차','프로세스','정책','workflow','booking','policy'],
 '가격·결제·환불':['가격','요금','결제','환불','매출','price','billing','refund'],
 '개발·기술':['개발','코드','api','오류','배포','code','debug'],
 '홍보·브랜드':['홍보','마케팅','광고','브랜드','marketing','brand'],
 '개인정보 주의':['가족','건강','병원','연애','개인','비밀번호','password','medical']
};
function hints(title){const t=title.toLowerCase(),keys=Object.keys(groups).filter(k=>groups[k].some(w=>t.includes(w)));return keys.length?keys:['미분류'];}
function messages(item){
 if(!item||typeof item.mapping!=='object'||!item.mapping||Array.isArray(item.mapping))throw Error('ChatGPT 대화 JSON 형식을 확인해 주세요.');
 const branch=[],visited=new Set();let id=item.current_node;
 while(typeof id==='string'&&Object.hasOwn(item.mapping,id)&&!visited.has(id)){
  visited.add(id);const node=item.mapping[id];if(!node||typeof node!=='object')break;branch.push(node);id=node.parent;
 }
 const out=[];
 for(const node of branch.reverse()){
  const m=node.message;if(!m||!['user','assistant'].includes(m.author?.role)||m.content?.content_type!=='text'||!Array.isArray(m.content.parts))continue;
  for(const part of m.content.parts)if(typeof part==='string'&&part.trim())out.push([m.author.role,part.trim().replace(/\s+/gu,' ')]);
 }
 return out;
}
async function inspect(files,start,end,progress){
 if(!Array.isArray(files)||!files.length||files.length>MAX_FILES||files.some(f=>f.size>MAX_FILE)||files.reduce((n,f)=>n+f.size,0)>MAX_TOTAL)throw Error('JSON은 파일당 128MiB, 전체 1GiB, 최대 20개입니다. 더 작은 파일로 나누어 선택하세요.');
 if(start&&end&&start>end)throw Error('날짜 범위를 확인해 주세요.');
 const seen=new Set(),conversations=[],encoder=new TextEncoder();let duplicates=0,excluded=0,count=0;
 for(let i=0;i<files.length;i++){
  progress('JSON '+(i+1)+'/'+files.length+' 확인 중');
  const items=JSON.parse(await files[i].text());if(!Array.isArray(items))throw Error('대화 배열 JSON이 필요합니다.');
  count+=items.length;if(count>MAX_COUNT)throw Error('한 번에 대화 30,000개까지 확인할 수 있습니다.');
  for(const item of items){
   const ms=messages(item);let date='';if(typeof item.create_time==='number'&&Number.isFinite(item.create_time)){const d=new Date(item.create_time*1000);if(!Number.isNaN(d.valueOf()))date=d.toISOString().slice(0,10);}
   if(!ms.length||(start&&(!date||date<start))||(end&&(!date||date>end))){excluded++;continue;}
   const data=encoder.encode(JSON.stringify(ms)),digest=await crypto.subtle.digest('SHA-256',data),id=Array.from(new Uint8Array(digest),x=>x.toString(16).padStart(2,'0')).join('');
   if(seen.has(id)){duplicates++;continue;}seen.add(id);
   const title=String(item.title||'제목 없음');
   conversations.push({id,title:title.slice(0,160),date,messages:ms.length,chars:ms.reduce((n,m)=>n+m[1].length,0),approxTokens:Math.ceil(data.length/3),categoryHints:hints(title),classification:'title_only'});
  }
 }
 return {conversations,duplicates,excluded};
}
self.onmessage=async ev=>{try{const {files,start,end}=ev.data;const result=await inspect(files,start,end,progress=>self.postMessage({progress}));self.postMessage({result});}catch(err){self.postMessage({error:err instanceof SyntaxError?'JSON 파일 형식이 올바르지 않습니다.':String(err.message||'파일 분석 실패')});}};
