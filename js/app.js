// Interfaz: carga de datos, renderizado y eventos.
const IMG=window.IMG||{};
let F=[],DATA={};
const sf=(f,k)=>{const[v]=sv(f,k);return v==null?"—":v+(SU[k]||"")};
const fd=d=>new Date(d+"T12:00:00").toLocaleDateString(L,{month:"short",year:"numeric"});
const pills=f=>(f.l5||[]).map(x=>`<i class="pl ${x[2]}" title="${x[1]} · ${x[3]}">${x[2]}</i>`).join("");
const stx=f=>SK.map(k=>`<div class="row"><span>${t(k)}</span><span>${sf(f,k)}</span></div>`).join("");
function init(){const ld=window.__DATA__?Promise.resolve(window.__DATA__):fetch("data/fighters.json").then(r=>{if(!r.ok)throw 0;return r.json()});
ld.then(d=>{DATA=d;F=d.fighters.map((f,i)=>({...f,id:i}));const hw=F.filter(f=>f.d==S.d);S.a=hw[0].id;S.b=hw[1].id;render()}).catch(()=>{document.querySelector("main").insertAdjacentHTML("afterbegin",'<p class="mu" style="padding:24px">No se pudo cargar data/fighters.json. Abrí el sitio desde un servidor (python -m http.server) o desde GitHub Pages.</p>')})}
const $=i=>document.getElementById(i),root=document.documentElement,idx=n=>F.find(f=>f.n==n).id;
let L="es",cur=7,vw=0,S={d:7,a:0,b:1};try{L=localStorage.getItem("l")||"es"}catch(e){}
const t=k=>T[L][k],ov=f=>Math.round((f.P+f.S+f.G+f.B+f.R)/5),tag=f=>f.k?"#"+f.k:t("C");
function av(f,s){if(IMG[f.n])return`<img src="${IMG[f.n]}" alt="${f.n}">`;let h=0;for(const c of f.n)h=(h*31+c.charCodeAt(0))%360;const i=f.n.split(" ").map(w=>w[0]).slice(0,2).join("");
return`<svg viewBox="0 0 100 100" role="img" aria-label="${f.n}"><rect width="100" height="100" fill="hsl(${h},18%,22%)"/><circle cx="50" cy="38" r="16" fill="hsl(${h},14%,40%)"/><path d="M16 100Q16 62 50 62Q84 62 84 100Z" fill="hsl(${h},14%,40%)"/><text x="50" y="92" text-anchor="middle" font-size="13" font-family="Oswald,sans-serif" fill="#fff" opacity=".85">${i}</text></svg>`}
function simR(){const a=F[S.a],b=F[S.b],r=sim(a,b),pa=Math.round(r.p*100),pb=100-pa,C=2*Math.PI*48;
const rows=["P","S","G","B","R"].map(k=>{const x=a[k],y=b[k];return`<div class="sr"><div class="${x>=y?"w":""}"><b>${x}</b><div class="bar rt"><i style="width:${x}%"></i></div></div><span>${t(k)}</span><div class="${y>=x?"w":""}"><b>${y}</b><div class="bar"><i style="width:${y}%"></i></div></div></div>`}).join("");
const lo={sapm:1},x2=SK.map(k=>{const[x,xr]=sv(a,k),[y,yr]=sv(b,k),ok=x!=null&&y!=null,aw=ok&&(lo[k]?x<y:x>y),bw=ok&&(lo[k]?y<x:y>x);return`<div class="sr"><div class="${aw?"w":""}"><b>${sf(a,k)}</b></div><span>${t(k)}</span><div class="${bw?"w":""}"><b>${sf(b,k)}</b></div></div>`}).join("");
const pl=f=>`<div>${av(f,0)}<h3>${f.n}</h3><span class="mu">${f.r} · ${t("sty")[f.s]}</span></div>`;
$("cmp").innerHTML=`<div><div class="vs">${pl(a)}<i>VS</i>${pl(b)}</div>${rows}<div class="mu" style="margin-top:14px">${t("xs")}</div>${x2}<div class="sr"><div>${pills(a)}</div><span>${t("l5")}</span><div>${pills(b)}</div></div></div><div class="cr"><svg viewBox="0 0 120 120"><circle cx="60" cy="60" r="48" fill="none" stroke="currentColor" stroke-opacity=".25" stroke-width="14"/><circle cx="60" cy="60" r="48" fill="none" stroke="var(--ac)" stroke-width="14" stroke-dasharray="${C*pa/100} ${C}" transform="rotate(-90 60 60)"/><text x="60" y="64" text-anchor="middle" font-size="26" font-weight="700" font-family="Oswald,sans-serif" fill="currentColor">${pa}%</text><text x="60" y="82" text-anchor="middle" font-size="11" fill="currentColor" opacity=".6">${pb}%</text></svg><div class="lg"><span><i style="background:var(--ac)"></i>${a.n} · ${pa}%</span><span><i style="background:currentColor;opacity:.3"></i>${b.n} · ${pb}%</span></div><p class="mu">${t("mT")}:<br>KO/TKO ${r.m[0]}% · SUB ${r.m[1]}% · DEC ${r.m[2]}%</p><p class="mu">${r.who} ${t(r.ek)}</p></div>`}
function sels(){const fs=F.filter(f=>f.d==S.d),o=f=>`<option value="${f.id}">${f.n}</option>`;
$("sd").innerHTML=K.map((k,d)=>`<option value="${d}">${t("dv")[d]} · ${W[d]}</option>`).join("");$("sd").value=S.d;$("sa").innerHTML=fs.map(o).join("");$("sb").innerHTML=fs.map(o).join("");$("sa").value=S.a;$("sb").value=S.b;simR()}
function render(){document.querySelectorAll("[data-i]").forEach(e=>e.textContent=t(e.dataset.i));root.lang=L;$("lb").textContent=L=="es"?"EN":"ES";$("mb").textContent=t("mn");$("upd").textContent=t("up")+": "+(DATA.updated||"");
$("mp").innerHTML=[0,1,2].map(i=>`<button data-go="${i}" class="${i==vw?"cur":""}">${t("n"+(i+1))}</button>`).join("");
$("st").innerHTML=t("s").map(s=>`<div><span class="n">${s[0]}</span>${s[1]}</div>`).join("");$("tl").innerHTML=t("tl").map(e=>`<div><b>${e[0]}</b><br>${e[1]}</div>`).join("");
ocRender();
$("tabs").innerHTML=K.map((k,d)=>`<button class="tab ${d==cur?"on":""}" data-d="${d}">${t("dv")[d]} · ${W[d]}</button>`).join("");
$("list").innerHTML=F.filter(f=>f.d==cur).map(f=>`<button class="f ${f.k?"":"c"}" data-f="${f.id}">${av(f,0)}<div class="t"><div class="rk">${tag(f)}</div><h3>${f.n}</h3><div class="mu">${f.c} · ${f.r}</div></div></button>`).join("");sels()}
function go(v){vw=v;document.querySelectorAll(".view").forEach((e,i)=>e.classList.toggle("on",i==v));$("mp").classList.remove("on");render();scrollTo(0,0)}
function open_(f){const bars=["P","S","G","B","R"].map(k=>`<div class="row"><span>${t(k)}</span><b>${f[k]}</b></div><div class="bar" style="margin-top:4px"><i style="width:${f[k]}%"></i></div>`).join("");
const l5=(f.l5||[]).map(x=>`<div class="row"><span><i class="pl ${x[2]}">${x[2]}</i> ${x[1]}</span><span>${x[3]}${x[4]?" R"+x[4]:""} · ${fd(x[0])}</span></div>`).join("");
$("dlg").innerHTML=`<div class="dd" style="padding:0">${av(f,0)}</div><div class="dd"><div class="rk">${tag(f)} · ${t("dv")[f.d]}</div><h3 style="font-size:26px;margin:2px 0">${f.n}</h3><div class="mu">${f.c} · ${t("rec")} ${f.r}${f.ufc?" (UFC "+f.ufc+")":""} · ${t("st")}: ${t("sty")[f.s]} · ${t("ov")} ${ov(f)}</div>${bars}<div class="row" style="margin-top:20px"><b>${t("xs")}</b></div>${stx(f)}<div class="row" style="margin-top:20px"><b>${t("l5")}</b></div>${l5}<p style="text-align:right;margin:18px 0 0"><button class="b" id="cx">${t("x")}</button></p></div>`;$("dlg").showModal();$("cx").onclick=()=>$("dlg").close()}
document.addEventListener("click",e=>{const g=e.target.closest("[data-go]"),d=e.target.closest("[data-d]"),f=e.target.closest("[data-f]");
if(g)go(+g.dataset.go);else if(d){cur=+d.dataset.d;render()}else if(f)open_(F[+f.dataset.f]);else if(e.target==$("dlg"))$("dlg").close();else if(!e.target.closest(".mn"))$("mp").classList.remove("on")});
$("mb").onclick=()=>$("mp").classList.toggle("on");$("lg").onclick=()=>go(0);
$("sd").onchange=e=>{S.d=+e.target.value;const fs=F.filter(f=>f.d==S.d);S.a=fs[0].id;S.b=fs[1].id;sels()};
$("sa").onchange=e=>{S.a=+e.target.value;if(S.a==S.b)S.b=F.find(f=>f.d==S.d&&f.id!=S.a).id;sels()};
$("sb").onchange=e=>{S.b=+e.target.value;if(S.a==S.b)S.a=F.find(f=>f.d==S.d&&f.id!=S.b).id;sels()};
$("lb").onclick=()=>{L=L=="es"?"en":"es";try{localStorage.setItem("l",L)}catch(e){}render()};
$("tb").onclick=()=>{root.dataset.theme=root.dataset.theme=="dark"?"light":"dark";try{localStorage.setItem("th",root.dataset.theme)}catch(e){}};
try{const th=localStorage.getItem("th");if(th)root.dataset.theme=th}catch(e){}
// ---- Carrusel: octágono 3D con las peleas inolvidables
let oN=0,oT=null,hov=false,dx0=null;const mod8=n=>((n%8)+8)%8,oc=$("oct");
function ocBuild(){let h='<div class="floor"><img alt=""></div>';for(let j=0;j<8;j++)h+=`<i class="post" style="--j:${j}"></i>`;for(let i=0;i<8;i++)h+=`<article class="face" style="--i:${i}"></article>`;
$("stage").innerHTML=h;$("stage").querySelector(".floor img").src=document.querySelector(".brand img").src}
function ocRender(){document.querySelectorAll("#stage .face").forEach((el,i)=>{const f=t("fs")[i];el.innerHTML=`<div class="fcard"><div class="fy"><b>${f[0]}</b><span>${String(i+1).padStart(2,"0")}/08</span></div><h3>${f[1]}</h3><div class="mu">${f[2]}</div><span class="fr">${f[3]}</span><p>${f[4]}</p></div>`});
$("dots").innerHTML=t("fs").map((f,i)=>`<button class="dot" data-n="${i}">${f[0]}</button>`).join("");ocGo(oN)}
function ocGo(n){oN=n;const i=mod8(n);$("stage").style.setProperty("--ry",-n*45+"deg");
document.querySelectorAll("#stage .face").forEach((el,k)=>{el.classList.toggle("act",k==i);el.setAttribute("aria-hidden",k!=i)});
document.querySelectorAll("#dots .dot").forEach((el,k)=>el.classList.toggle("on",k==i))}
const ocStop=()=>{clearInterval(oT);oT=null};
$("next").onclick=()=>{ocStop();ocGo(oN+1)};$("prev").onclick=()=>{ocStop();ocGo(oN-1)};
$("dots").onclick=e=>{const b=e.target.closest(".dot");if(!b)return;ocStop();let d=+b.dataset.n-mod8(oN);if(d>4)d-=8;if(d<-4)d+=8;ocGo(oN+d)};
oc.onkeydown=e=>{if(e.key=="ArrowRight")$("next").click();if(e.key=="ArrowLeft")$("prev").click()};
oc.onpointerdown=e=>{if(e.target.closest(".oc"))return;dx0=e.clientX;oc.classList.add("drag");ocStop()};
oc.onpointermove=e=>{if(dx0!=null)$("stage").style.setProperty("--ry",(-oN*45+(e.clientX-dx0)*.25)+"deg")};
const dragEnd=e=>{if(dx0==null)return;const d=e.clientX-dx0;dx0=null;oc.classList.remove("drag");ocGo(oN+(d<-40?1:d>40?-1:0))};
oc.onpointerup=oc.onpointercancel=oc.onpointerleave=dragEnd;oc.onmouseenter=()=>hov=true;oc.onmouseleave=()=>hov=false;
ocBuild();if(!matchMedia("(prefers-reduced-motion: reduce)").matches)oT=setInterval(()=>{if(!hov&&!document.hidden)ocGo(oN+1)},9000);
init();
