// Страница устройства. Без внешних библиотек и шрифтов: должна открываться и через точку
// доступа устройства, где нет интернета. Хранится во flash (PROGMEM).
#pragma once

#include <Arduino.h>

const char PAGE[] PROGMEM = R"rawliteral(<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="dark light">
<title>ЕмПолимер</title>
<style>
:root{--bg:#0d1117;--card:#161b22;--line:#30363d;--text:#e6edf3;--muted:#8b949e;--ok:#3fb950;--low:#58a6ff;--high:#f0883e;--bad:#f85149;--accent:#2ea043}
@media (prefers-color-scheme:light){:root{--bg:#f4f6f8;--card:#fff;--line:#d8dee4;--text:#1f2328;--muted:#656d76;--ok:#1a7f37;--low:#0969da;--high:#bc4c00;--bad:#cf222e;--accent:#2e7d5b}}
*{box-sizing:border-box}[hidden]{display:none!important}
body{margin:0;background:var(--bg);color:var(--text);font:15px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
header{display:flex;align-items:center;gap:10px;flex-wrap:wrap;padding:14px 18px;border-bottom:1px solid var(--line)}
h1{font-size:19px;margin:0}.sub{color:var(--muted);font-size:13px}.grow{flex:1}
main{display:grid;gap:14px;padding:16px 18px;max-width:1100px;margin:0 auto;grid-template-columns:repeat(auto-fit,minmax(300px,1fr))}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px}
.wide{grid-column:1/-1}
.pill{display:inline-flex;align-items:center;gap:6px;padding:3px 10px;border-radius:99px;border:1px solid var(--line);font-size:13px;white-space:nowrap}
.dot{width:8px;height:8px;border-radius:50%;background:var(--muted);flex:none}
.ok .dot{background:var(--ok)}.bad .dot{background:var(--bad)}
.metrics{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.metric{border-width:2px}.label{color:var(--muted);font-size:13px}
.value{font-size:44px;font-weight:700;line-height:1.1;margin:2px 0;font-variant-numeric:tabular-nums}
.value small{font-size:18px;font-weight:500;margin-left:4px}.hint{font-size:13px}
.updated{color:var(--muted);font-size:13px;margin-top:8px}.stale{color:var(--high)}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:8px 14px;font-size:14px}
.item{display:flex;align-items:center;gap:8px}.detail{color:var(--muted);font-size:12px}
.chart-head{display:flex;flex-wrap:wrap;gap:2px 10px;justify-content:space-between;align-items:baseline;margin-bottom:6px}
.stats{color:var(--muted);font-size:12px}
svg{width:100%;height:170px;display:block}
.seg{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:10px}
.seg button{padding:11px;border-radius:10px;border:1px solid var(--line);background:transparent;color:var(--text);font:inherit;cursor:pointer}
.seg button.active{background:var(--accent);border-color:var(--accent);color:#fff}
.seg button:disabled{opacity:.45;cursor:not-allowed}
table{width:100%;border-collapse:collapse;font-size:14px}td{padding:6px 0;border-top:1px solid var(--line)}
td:last-child{text-align:right;color:var(--muted)}a{color:var(--low)}
.banner{margin:12px 18px 0;padding:10px 14px;border-radius:10px;color:var(--bad);border:1px solid var(--bad)}
.info td:first-child{color:var(--muted)}.info td:last-child{color:var(--text)}
</style>
</head>
<body>
<header>
  <div><h1>ЕмПолимер · <span id="id">…</span></h1><div class="sub" id="where"></div></div>
  <div class="grow"></div>
  <span class="pill" id="sensor"><span class="dot"></span><span>Датчик</span></span>
  <span class="pill" id="clock"></span>
</header>
<div class="banner" id="offline" hidden>Нет связи с устройством - показаны последние данные.</div>
<main>
  <section class="wide">
    <div class="metrics">
      <div class="card metric" id="temp"><div class="label">Температура</div><div class="value">-</div><div class="hint"></div></div>
      <div class="card metric" id="hum"><div class="label">Влажность</div><div class="value">-</div><div class="hint"></div></div>
    </div>
    <div class="updated" id="updated"></div>
  </section>
  <section class="card">
    <div class="chart-head"><strong>Температура</strong><span class="stats" id="temp-stats"></span></div>
    <svg id="temp-chart" viewBox="0 0 400 170" preserveAspectRatio="none"></svg>
  </section>
  <section class="card">
    <div class="chart-head"><strong>Влажность</strong><span class="stats" id="hum-stats"></span></div>
    <svg id="hum-chart" viewBox="0 0 400 170" preserveAspectRatio="none"></svg>
  </section>
  <section class="card">
    <strong>Модули</strong>
    <div class="grid2" id="modules" style="margin-top:10px"></div>
  </section>
  <section class="card">
    <div class="chart-head"><strong>Подсветка</strong><span class="stats" id="light-state"></span></div>
    <div class="seg"><button data-mode="on">Включить</button><button data-mode="off">Выключить</button><button data-mode="auto">Авто</button></div>
    <div class="detail" id="light-note" style="margin-top:8px"></div>
  </section>
  <section class="card">
    <strong>Журналы на SD-карте</strong>
    <table id="files"></table>
  </section>
  <section class="card">
    <strong>Устройство</strong>
    <table class="info" id="info"></table>
  </section>
</main>
<script>
const $=s=>document.querySelector(s);
const LV={ok:['var(--ok)','в норме'],low:['var(--low)','ниже нормы'],high:['var(--high)','выше нормы']};
let st=null,fails=0;
const fmt=(v,d=1)=>v==null?'-':Number(v).toLocaleString('ru-RU',{minimumFractionDigits:d,maximumFractionDigits:d});
const ago=s=>s==null?'измерений ещё не было':s<5?'только что':s<60?s+' с назад':s<3600?Math.floor(s/60)+' мин назад':Math.floor(s/3600)+' ч '+Math.floor(s%3600/60)+' мин назад';
const level=(v,a,b)=>v==null?null:v<a?'low':v>b?'high':'ok';
const up=s=>{const d=Math.floor(s/86400),h=Math.floor(s%86400/3600),m=Math.floor(s%3600/60);return (d?d+' д ':'')+(h?h+' ч ':'')+m+' мин'};
function metric(id,v,unit,a,b){
  const c=$('#'+id),l=level(v,a,b),[col,txt]=LV[l]||['var(--muted)','нет данных'];
  c.querySelector('.value').innerHTML=v==null?'-':fmt(v)+'<small>'+unit+'</small>';
  c.querySelector('.value').style.color=col;
  c.querySelector('.hint').textContent=txt+' · '+a+'–'+b+' '+unit;
  c.querySelector('.hint').style.color=col;
  c.style.borderColor=l&&l!='ok'?col:'';
}
const item=(name,ok,detail='')=>'<div class="item '+(ok==null?'':ok?'ok':'bad')+'"><span class="dot"></span>'+name+(detail?' <span class="detail">'+detail+'</span>':'')+'</div>';
function render(){
  const s=st,r=s.reading||{},n=s.norm;
  $('#id').textContent=s.id;
  $('#where').textContent=s.wifi?(s.host+'.local · '+s.ip):(s.ap?'точка доступа EmPolimer-'+s.id:'без Wi-Fi');
  $('#sensor').className='pill '+(s.sensor?'ok':'bad');
  $('#sensor').lastElementChild.textContent=s.sensor?'Датчик работает':'Датчик не отвечает';
  metric('temp',r.temp,'°C',n.temp_min,n.temp_max);
  metric('hum',r.hum,'%',n.hum_min,n.hum_max);
  const stale=r.age!=null&&r.age>Math.max(3*s.interval,120);
  $('#updated').textContent='Обновлено: '+ago(r.age)+(stale?' - данные устарели':'');
  $('#updated').className='updated'+(stale?' stale':'');
  $('#modules').innerHTML=[
    item('Wi-Fi',s.wifi,s.wifi?s.rssi+' дБм':''),item('Сервер',s.mqtt,s.queue?'очередь '+s.queue:''),
    item('SD-карта',s.sd),item('Часы',s.time),item('Точка доступа',s.ap?true:null,s.ap?'включена':'выключена')].join('');
  $('#light-state').textContent=(s.light?'включена':'выключена')+' · '+(s.light_auto?'по расписанию':'вручную');
  document.querySelectorAll('.seg button').forEach(b=>{const m=b.dataset.mode;
    b.classList.toggle('active',m=='auto'?s.light_auto:!s.light_auto&&(m=='on')==s.light);b.disabled=!s.control});
  $('#light-note').textContent=s.control?'':'Управление со страницы выключено в config.json (web.control)';
  $('#info').innerHTML=[['Прошивка',s.fw+' · '+s.board],['Работает',up(s.uptime)],['Измерение','раз в '+s.interval+' с'],
    ['Адрес',s.wifi?s.ip:'-'],r.bat!=null?['Батарея',fmt(r.bat,2)+' В']:null,s.config_error?['Ошибка config.json',s.config_error]:null]
    .filter(Boolean).map(([a,b])=>'<tr><td>'+a+'</td><td>'+b+'</td></tr>').join('');
  $('#clock').textContent=s.now?new Date(s.now*1000).toLocaleTimeString('ru-RU',{hour:'2-digit',minute:'2-digit'}):'часы не установлены';
}
function chart(id,points,idx,unit,color,a,b){
  const svg=$('#'+id),W=400,H=170,P=26;
  if(!points.length){svg.innerHTML='<text x="200" y="90" text-anchor="middle" fill="var(--muted)" font-size="13">измерений пока нет</text>';return null}
  const vals=points.map(p=>p[idx]),t=points.map(p=>-p[0]);
  let lo=Math.min(...vals,a),hi=Math.max(...vals,b);const pad=(hi-lo)*.1||1;lo-=pad;hi+=pad;
  const t0=Math.min(...t),t1=Math.max(0,...t),x=v=>P+(v-t0)/((t1-t0)||1)*(W-P-6),y=v=>H-18-(v-lo)/(hi-lo)*(H-28);
  let path='',prev=null;const gap=Math.max(3*(points.interval||60),180);
  points.forEach((p,i)=>{const cmd=prev!=null&&(prev-p[0])>gap?'M':(i?'L':'M');path+=cmd+x(-p[0]).toFixed(1)+' '+y(p[idx]).toFixed(1);prev=p[0]});
  const band='<rect x="'+P+'" y="'+y(b)+'" width="'+(W-P-6)+'" height="'+(y(a)-y(b))+'" fill="var(--ok)" opacity=".08"/>';
  const grid=[a,b].map(v=>'<line x1="'+P+'" x2="'+(W-6)+'" y1="'+y(v)+'" y2="'+y(v)+'" stroke="var(--muted)" stroke-dasharray="4 4" stroke-width=".8"/><text x="'+(P-4)+'" y="'+(y(v)+4)+'" font-size="10" text-anchor="end" fill="var(--muted)">'+v+'</text>').join('');
  const span=t1-t0,lab=span>=3600?Math.round(span/3600)+' ч назад':Math.round(span/60)+' мин назад';
  const axis='<text x="'+P+'" y="'+(H-3)+'" font-size="10" fill="var(--muted)">'+lab+'</text><text x="'+(W-6)+'" y="'+(H-3)+'" font-size="10" text-anchor="end" fill="var(--muted)">сейчас</text>';
  svg.innerHTML=band+grid+axis+'<path d="'+path+'" fill="none" stroke="'+color+'" stroke-width="2" vector-effect="non-scaling-stroke"/>';
  const avg=vals.reduce((s,v)=>s+v,0)/vals.length;
  return 'мин '+fmt(Math.min(...vals))+' · ср '+fmt(avg)+' · макс '+fmt(Math.max(...vals))+' '+unit;
}
async function poll(){
  try{const r=await fetch('/api/state',{cache:'no-store'});if(!r.ok)throw 0;st=await r.json();fails=0;$('#offline').hidden=true;render()}
  catch(e){if(++fails>=2)$('#offline').hidden=false}
}
async function history(){
  try{const r=await fetch('/api/history',{cache:'no-store'});const h=await r.json();h.points.interval=h.interval;
    const n=st?st.norm:{temp_min:18,temp_max:28,hum_min:40,hum_max:70};
    $('#temp-stats').textContent=chart('temp-chart',h.points,1,'°C','var(--high)',n.temp_min,n.temp_max)||'';
    $('#hum-stats').textContent=chart('hum-chart',h.points,2,'%','var(--low)',n.hum_min,n.hum_max)||''}catch(e){}
}
async function files(){
  try{const r=await fetch('/api/files');const f=await r.json();
    $('#files').innerHTML=!f.sd?'<tr><td>SD-карта не найдена</td><td></td></tr>':!f.files.length?'<tr><td>Журналов пока нет</td><td></td></tr>':
    f.files.sort((a,b)=>(a.name<'a')==(b.name<'a')?b.name.localeCompare(a.name):a.name<'a'?-1:1).map(x=>'<tr><td><a href="/log/'+x.name+'" download>'+x.name+'</a></td><td>'+(x.size/1024).toFixed(1)+' КБ</td></tr>').join('')}catch(e){}
}
document.querySelectorAll('.seg button').forEach(b=>b.onclick=async()=>{
  try{const r=await fetch('/api/light',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:'mode='+b.dataset.mode});
    if(!r.ok)$('#light-note').textContent=(await r.json()).detail}catch(e){$('#light-note').textContent='Нет связи с устройством'}
  setTimeout(poll,500)});
poll().then(history);files();
setInterval(poll,3000);setInterval(history,30000);setInterval(files,60000);
</script>
</body>
</html>
)rawliteral";
