/*
 * frontend/mock.js
 * ───────────────────────────────────────────────────────────────────────
 * 백엔드 미연결 시 사용하는 프론트 목업. 백엔드 app/services/mock_data.py 와
 * 동일한 궁합표·감정 로직을 담아, 오프라인에서도 같은 결과가 나오게 합니다.
 * (배포해 API_BASE를 채우면 이 파일은 폴백 용도로만 남습니다.)
 */

export const PEOPLE = {
  jesus:{id:"jesus",name:"예수 그리스도",mbti:"INFJ",role:"선한 목자",traits:"통찰 · 사랑 · 사명",epithet:"임마누엘 · 길이요 진리요 생명",quote:"수고하고 무거운 짐 진 자들아 다 내게로 오라 내가 너희를 쉬게 하리라",quote_ref:"마태복음 11:28",books:["마태복음","요한복음"]},
  peter:{id:"peter",name:"베드로",mbti:"ESFP",role:"반석",traits:"열정 · 회복 · 행동",epithet:"반석(게바) · 천국 열쇠를 받은 자",quote:"주는 그리스도시요 살아 계신 하나님의 아들이시니이다",quote_ref:"마태복음 16:16",books:["마태복음","베드로전서"]},
  john:{id:"john",name:"요한",mbti:"INFP",role:"사랑받는 제자",traits:"사랑 · 관계 · 깊은 묵상",epithet:"사랑의 사도 · 예수의 사랑하시는 제자",quote:"사랑하는 자들아 우리가 서로 사랑하자 사랑은 하나님께 속한 것이니",quote_ref:"요한1서 4:7",books:["요한복음","요한1서"]},
  james:{id:"james",name:"야고보",mbti:"ENTJ",role:"천둥의 아들",traits:"신념 · 추진력",epithet:"보아너게 · 우레의 아들",quote:"주여 우리가 하늘로부터 불을 명하여 저들을 멸하라 하기를 원하시나이까",quote_ref:"누가복음 9:54",books:["누가복음","마가복음"]},
  andrew:{id:"andrew",name:"안드레",mbti:"ISFJ",role:"연결자",traits:"조용한 섬김 · 소개",epithet:"첫 부르심 · 사람을 잇는 자",quote:"우리가 메시야를 만났다",quote_ref:"요한복음 1:41",books:["요한복음"]},
  philip:{id:"philip",name:"빌립",mbti:"ISTJ",role:"확인하는 자",traits:"현실적 · 계산 · 확인",epithet:"와서 보라 · 확인하는 자",quote:"주여 아버지를 우리에게 보여 주옵소서 그리하면 족하겠나이다",quote_ref:"요한복음 14:8",books:["요한복음"]},
  bartholomew:{id:"bartholomew",name:"바돌로매",mbti:"ISTJ",role:"참된 자",traits:"정직 · 순수 · 원칙",epithet:"나다나엘 · 간사함이 없는 자",quote:"랍비여 당신은 하나님의 아들이시요 당신은 이스라엘의 임금이로소이다",quote_ref:"요한복음 1:49",books:["요한복음"]},
  matthew:{id:"matthew",name:"마태",mbti:"INTJ",role:"기록하는 자",traits:"분석 · 기록 · 변화 경험",epithet:"레위 · 복음을 기록한 세리",quote:"일어나 그를 좇으니라",quote_ref:"마태복음 9:9",books:["마태복음"]},
  thomas:{id:"thomas",name:"도마",mbti:"INTP",role:"묻는 자",traits:"의심 · 검증 · 확신 추구",epithet:"디두모 · 검증하는 자",quote:"나의 주님이시요 나의 하나님이시니이다",quote_ref:"요한복음 20:28",books:["요한복음"]},
  james_alph:{id:"james_alph",name:"작은 야고보",mbti:"ISFJ",role:"조용한 증인",traits:"드러나지 않는 충성",epithet:"작은 자 · 드러나지 않는 충성",quote:"행함이 없는 믿음은 그 자체가 죽은 것이라",quote_ref:"야고보서 2:17",books:["야고보서"]},
  thaddaeus:{id:"thaddaeus",name:"다대오",mbti:"ENFP",role:"질문하는 자",traits:"질문 · 공동체 관심",epithet:"유다(가룟인 아닌) · 묻는 마음",quote:"주여 어찌하여 자기를 우리에게는 나타내시고 세상에는 아니하려 하시나이까",quote_ref:"요한복음 14:22",books:["요한복음"]},
  simon:{id:"simon",name:"시몬",mbti:"ESTP",role:"열심당원",traits:"열정 · 신념 · 행동파",epithet:"셀롯 · 열심 있는 자",quote:"열심으로 하나님을 섬기던 자, 이제 그 열심을 복음에 쏟다",quote_ref:"누가복음 6:15",books:["누가복음"]},
  judas:{id:"judas",name:"가룟 유다",mbti:"ENTJ",role:"회계",traits:"계산 · 현실 감각",epithet:"가룟 사람 · 돈궤를 맡은 자",quote:"내가 무죄한 피를 팔고 죄를 범하였도다",quote_ref:"마태복음 27:4",books:["마태복음"]},
};

const TYPE_ORDER=["INFJ","INFP","INTJ","INTP","ENFJ","ENFP","ENTJ","ENTP","ISFJ","ISFP","ISTJ","ISTP","ESFJ","ESFP","ESTJ","ESTP"];
const SCORES={
  INFJ:[72,92,78,85,92,100,85,98,49,56,42,49,56,63,49,56],INFP:[92,72,85,78,100,92,98,85,56,49,49,42,63,56,56,49],
  INTJ:[78,85,72,92,85,98,92,100,42,49,49,56,49,56,56,63],INTP:[85,78,92,72,98,85,100,92,49,42,56,49,56,49,63,56],
  ENFJ:[92,100,85,98,72,92,78,85,56,63,49,56,49,56,42,49],ENFP:[100,92,98,85,92,72,85,78,63,56,56,49,56,49,49,42],
  ENTJ:[85,98,92,100,78,85,72,92,49,56,56,63,42,49,49,56],ENTP:[98,85,100,92,85,78,92,72,56,49,63,56,49,42,56,49],
  ISFJ:[49,56,42,49,56,63,49,56,72,92,78,85,92,100,85,98],ISFP:[56,49,49,42,63,56,56,49,92,72,85,78,100,92,98,85],
  ISTJ:[42,49,49,56,49,56,56,63,78,85,72,92,85,98,92,100],ISTP:[49,42,56,49,56,49,63,56,85,78,92,72,98,85,100,92],
  ESFJ:[56,63,49,56,49,56,42,49,92,100,85,98,72,92,78,85],ESFP:[63,56,56,49,56,49,49,42,100,92,98,85,92,72,85,78],
  ESTJ:[49,56,56,63,42,49,49,56,85,98,92,100,78,85,72,92],ESTP:[56,49,63,56,49,42,56,49,98,85,100,92,85,78,92,72],
};
const EMO_LABEL={anxiety:"불안",sadness:"슬픔",anger:"분노",joy:"기쁨",doubt:"의문",decision:"고민",neutral:"이야기"};
const EMO_KW={
  anxiety:["불안","걱정","두렵","무서","초조","막막","긴장"],sadness:["슬프","우울","눈물","외로","공허","지치","힘들","지쳐","허무"],
  anger:["화","짜증","억울","분노","열받","미워","원망"],joy:["감사","기쁘","행복","설레","좋아","고마","뿌듯"],
  doubt:["의심","확신","정말","증거","왜","이해가","믿기"],decision:["결정","선택","고민","어떻게","방향","진로","갈림길"],
};
const EMO_BIAS={anxiety:["john","andrew","james_alph"],sadness:["john","andrew","peter"],anger:["james","simon","matthew"],joy:["peter","thaddaeus"],doubt:["thomas","matthew","philip"],decision:["matthew","james","philip"],neutral:["john","peter","thaddaeus"]};

function compat(a,b){ if(!SCORES[a]) return 50; return SCORES[a][TYPE_ORDER.indexOf(b)]; }
export function bestMbti(m,limit=3){ if(!SCORES[m]) return []; return TYPE_ORDER.map((t,i)=>[t,SCORES[m][i]]).filter(([t])=>t!==m).sort((x,y)=>y[1]-x[1]).slice(0,limit).map(([t])=>t); }
function inferEmotion(text){ for(const[e,ws]of Object.entries(EMO_KW)){ if(ws.some(w=>text.includes(w))) return e; } return "neutral"; }

const MOCK_VERSES={
  anxiety:[{book:"빌립보서",chapter:4,verse:6,content:"아무 것도 염려하지 말고 다만 모든 일에 기도와 간구로 너희 구할 것을 감사함으로 하나님께 아뢰라"},{book:"이사야",chapter:41,verse:10,content:"두려워하지 말라 내가 너와 함께 함이라 놀라지 말라 나는 네 하나님이 됨이라"}],
  sadness:[{book:"시편",chapter:34,verse:18,content:"여호와는 마음이 상한 자를 가까이 하시고 충심으로 통회하는 자를 구원하시는도다"},{book:"마태복음",chapter:11,verse:28,content:"수고하고 무거운 짐 진 자들아 다 내게로 오라 내가 너희를 쉬게 하리라"}],
  doubt:[{book:"요한복음",chapter:20,verse:27,content:"믿음 없는 자가 되지 말고 믿는 자가 되라"}],
  neutral:[{book:"잠언",chapter:3,verse:5,content:"너는 마음을 다하여 여호와를 신뢰하고 네 명철을 의지하지 말라"}],
};
function versesFor(emo){ const vs=MOCK_VERSES[emo]||MOCK_VERSES.neutral; return vs.map(v=>({...v,source:`${v.book} ${v.chapter}:${v.verse}`})); }
function personaAnswer(p,emoLabel,msg){
  const lines={peter:`그 마음 잘 안다네. 나도 파도 앞에서 흔들렸던 사람 아닌가. 그 ${emoLabel}, 여기 내려놓게.`,
    john:`그 ${emoLabel}을(를) 여기 다 내려놓아도 괜찮아요. 사랑은 언제나 우리를 먼저 품는답니다.`,
    thomas:`의심이 드는 게 당연해요. 함께 하나씩 짚어봅시다. 확인하고 나면 마음이 한결 가벼워질 거예요.`,
    james:`핵심부터 짚어보세. 그 ${emoLabel} 뒤에 진짜 원하는 게 무엇인가?`};
  return lines[p.id]||`${p.name}(이)가 당신의 ${emoLabel}에 조용히 귀 기울입니다. 편히 이야기해 보세요.`;
}

/* ── api.js 와 동일한 시그니처의 목업 함수들 ─────────────────────────── */
let _users={};
export function signup({email,name,gender,mbti}){ _users[email]={email,name,gender,mbti:mbti.toUpperCase()}; return {token:"mock-"+email,user:_users[email]}; }
export function login({email}){ const u=_users[email]||{email,name:"손님",gender:"adam",mbti:"INFP"}; return {token:"mock-"+email,user:u}; }

export function recommend(message,userMbti="INFJ",emoWeight=1){
  const emo=inferEmotion(message); const bias=EMO_BIAS[emo]||[];
  const ranked=Object.values(PEOPLE).filter(p=>p.id!=="jesus").map(p=>{
    const c=compat(userMbti,p.mbti)/25; const rank=bias.includes(p.id)?3-bias.indexOf(p.id):0;
    return {...p,best_mbti:bestMbti(p.mbti),compat:+c.toFixed(2),score:+(c+rank*0.6*emoWeight).toFixed(3)};
  }).sort((a,b)=>b.score-a.score);
  return {emotion:emo,emotion_label:EMO_LABEL[emo],ranked};
}
export function answer(personId,message){
  const emo=inferEmotion(message); const p=PEOPLE[personId]||{id:personId,name:personId};
  return {person_id:personId,person_name:p.name,answer:personaAnswer(p,EMO_LABEL[emo],message),verses:versesFor(emo)};
}
export function getPeople(){ return Object.values(PEOPLE); }
export function matchMbti(mbti){ const r=recommend("",mbti).ranked.slice(0,3); return {mbti:mbti.toUpperCase(),matches:r}; }
export function getGraph(){
  const nodes=[],edges=[];
  TYPE_ORDER.forEach(t=>nodes.push({id:`mbti:${t}`,label:t,type:"mbti"}));
  Object.values(PEOPLE).forEach(p=>{ nodes.push({id:`person:${p.id}`,label:p.name,type:"person",mbti:p.mbti}); edges.push({source:`person:${p.id}`,target:`mbti:${p.mbti}`,kind:"has_mbti"}); });
  TYPE_ORDER.forEach(t=>{ const b=bestMbti(t,1); if(b[0]) edges.push({source:`mbti:${t}`,target:`mbti:${b[0]}`,kind:"compat"}); });
  return {nodes,edges};
}
