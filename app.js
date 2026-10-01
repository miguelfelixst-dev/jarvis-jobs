const state={jobs:[],updated_at:null};
const els={
  jobs:document.querySelector('#jobs'),tpl:document.querySelector('#jobTemplate'),
  search:document.querySelector('#search'),source:document.querySelector('#source'),
  minScore:document.querySelector('#minScore'),total:document.querySelector('#totalJobs'),
  hot:document.querySelector('#hotJobs'),updated:document.querySelector('#lastUpdate'),
  empty:document.querySelector('#empty'),dot:document.querySelector('#statusDot'),
  status:document.querySelector('#statusText')
};

function esc(s=''){return String(s)}
function fmtDate(s){
  if(!s)return 'Data não informada';
  const d=new Date(s); if(Number.isNaN(d.getTime())) return s;
  return d.toLocaleString('pt-BR',{dateStyle:'short',timeStyle:'short'});
}
function scoreClass(score){return score>=80?'🔥':score>=60?'🟢':score>=40?'🟡':'⚪'}
function render(){
  const q=els.search.value.toLowerCase().trim();
  const source=els.source.value;
  const min=Number(els.minScore.value||0);
  const filtered=state.jobs.filter(j=>{
    const blob=`${j.title} ${j.description} ${(j.tags||[]).join(' ')}`.toLowerCase();
    return (!q||blob.includes(q))&&(!source||j.source===source)&&(Number(j.score||0)>=min);
  });
  els.jobs.innerHTML='';
  els.empty.hidden=filtered.length>0;
  for(const j of filtered){
    const node=els.tpl.content.cloneNode(true);
    node.querySelector('.score').textContent=`${scoreClass(j.score)} SCORE ${j.score}`;
    node.querySelector('.source').textContent=j.source||'Fonte';
    node.querySelector('h2').textContent=j.title||'Sem título';
    node.querySelector('.description').textContent=j.description||'Sem descrição disponível.';
    const tags=node.querySelector('.tags');
    for(const t of (j.tags||[]).slice(0,8)){
      const span=document.createElement('span'); span.className='tag'; span.textContent=t; tags.appendChild(span);
    }
    node.querySelector('.date').textContent=fmtDate(j.date);
    const a=node.querySelector('a'); a.href=j.url; 
    els.jobs.appendChild(node);
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
    els.empty.hidden=false; els.empty.textContent='Ainda não há dados. Execute o workflow do radar no GitHub Actions.';
  }
}
for(const e of [els.search,els.source,els.minScore])e.addEventListener('input',render);
init();
