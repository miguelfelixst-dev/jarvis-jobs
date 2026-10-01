const state={jobs:[],updated_at:null};
const els={
  jobs:document.querySelector('#jobs'),tpl:document.querySelector('#jobTemplate'),
  search:document.querySelector('#search'),source:document.querySelector('#source'),
  minScore:document.querySelector('#minScore'),total:document.querySelector('#totalJobs'),
  hot:document.querySelector('#hotJobs'),updated:document.querySelector('#lastUpdate'),
  empty:document.querySelector('#empty'),dot:document.querySelector('#statusDot'),
  status:document.querySelector('#statusText')
};

const CACHE_KEY='jarvis_jobs_translation_cache_v1';
let translationCache={};
try{translationCache=JSON.parse(localStorage.getItem(CACHE_KEY)||'{}')}catch{translationCache={}}

function fmtDate(s){
  if(!s)return 'Data não informada';
  const d=new Date(s); if(Number.isNaN(d.getTime())) return s;
  return d.toLocaleString('pt-BR',{dateStyle:'short',timeStyle:'short'});
}
function scoreClass(score){return score>=80?'🔥':score>=60?'🟢':score>=40?'🟡':'⚪'}
function looksPortuguese(text=''){
  const t=text.toLowerCase();
  return /\b(para|com|uma|você|trabalho|dados|empresa|experiência|remoto|contrato|vaga|equipe|projeto)\b/.test(t);
}
function cacheSave(){
  try{
    const keys=Object.keys(translationCache);
    if(keys.length>900){
      const trimmed={};
      keys.slice(-700).forEach(k=>trimmed[k]=translationCache[k]);
      translationCache=trimmed;
    }
    localStorage.setItem(CACHE_KEY,JSON.stringify(translationCache));
  }catch{}
}
async function translateText(text){
  if(!text||looksPortuguese(text))return text;
  const key='pt:'+text;
  if(translationCache[key])return translationCache[key];
  const url='https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=pt&dt=t&q='+encodeURIComponent(text);
  const res=await fetch(url);
  if(!res.ok)throw new Error('Falha na tradução');
  const data=await res.json();
  const translated=(data?.[0]||[]).map(x=>x?.[0]||'').join('').trim();
  if(translated){
    translationCache[key]=translated;
    cacheSave();
    return translated;
  }
  return text;
}
async function translateCard(article,j){
  const titleEl=article.querySelector('h2');
  const descEl=article.querySelector('.description');
  const btn=article.querySelector('.translation-status');
  try{
    btn.textContent='Traduzindo...';
    const [title,desc]=await Promise.all([
      translateText(j.title||''),
      translateText((j.description||'').slice(0,650))
    ]);
    titleEl.textContent=title||j.title||'Sem título';
    descEl.textContent=desc||j.description||'Sem descrição disponível.';
    btn.textContent='Português automático';
  }catch{
    btn.textContent='Original em inglês';
    btn.title='A tradução automática não respondeu agora. O texto original foi mantido.';
  }
}
function render(){
  const q=els.search.value.toLowerCase().trim();
  const source=els.source.value;
  const min=Number(els.minScore.value||0);
  const filtered=state.jobs.filter(j=>{
    const blob=`${j.title} ${j.description} ${j.category||''} ${(j.tags||[]).join(' ')}`.toLowerCase();
    return (!q||blob.includes(q))&&(!source||j.source===source)&&(Number(j.score||0)>=min);
  });
  els.jobs.innerHTML='';
  els.empty.hidden=filtered.length>0;
  for(const j of filtered){
    const frag=els.tpl.content.cloneNode(true);
    const article=frag.querySelector('.job');
    article.querySelector('.score').textContent=`${scoreClass(j.score)} SCORE ${j.score}`;
    article.querySelector('.source').textContent=(j.category ? j.category+' • ' : '')+(j.source||'Fonte');
    article.querySelector('h2').textContent=j.title||'Sem título';
    article.querySelector('.description').textContent=j.description||'Sem descrição disponível.';
    const tags=article.querySelector('.tags');
    for(const t of (j.tags||[]).slice(0,8)){
      const span=document.createElement('span'); span.className='tag'; span.textContent=t; tags.appendChild(span);
    }
    const meta=j.meta||{};
    const bits=[];
    if(meta.competition!==null && meta.competition!==undefined) bits.push(meta.competition+' '+(meta.competition_label||'propostas'));
    if(meta.budget) bits.push(meta.budget);
    article.querySelector('.date').textContent=[fmtDate(j.date),...bits].join(' • ');
    const a=article.querySelector('a'); a.href=j.url;
    a.textContent='Abrir oportunidade';
    els.jobs.appendChild(frag);
    translateCard(article,j);
  }
}
async function init(){
  try{
    const res=await fetch(`data/jobs.json?v=${Date.now()}`);
    if(!res.ok)throw new Error('Falha ao carregar dados');
    const data=await res.json();
    state.jobs=(data.jobs||[]).sort((a,b)=>(b.score||0)-(a.score||0));
    state.updated_at=data.updated_at;
    const sources=[...new Set(state.jobs.map(j=>j.source).filter(Boolean))].sort();
    for(const s of sources){const o=document.createElement('option');o.value=s;o.textContent=s;els.source.appendChild(o)}
    els.total.textContent=state.jobs.length;
    els.hot.textContent=state.jobs.filter(j=>Number(j.score)>=70).length;
    els.updated.textContent=state.updated_at?fmtDate(state.updated_at):'—';
    els.dot.style.background='#22c55e'; els.status.textContent='Radar online';
    render();
  }catch(e){
    els.dot.style.background='#ef4444'; els.status.textContent='Erro ao carregar radar';
    els.empty.hidden=false; els.empty.textContent='Ainda não há dados disponíveis.';
  }
}
for(const e of [els.search,els.source,els.minScore])e.addEventListener('input',render);
init();
