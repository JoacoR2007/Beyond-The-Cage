// Modelo: constantes de divisiones, estimaciones y simulador de combate.
const W=[125,135,145,155,170,185,205,265],K=["FLY","BW","FW","LW","WW","MW","LHW","HW"];
const SK=["reach","slpm","acc","sapm","def","tdavg","tdacc","tddef","sub"],SU={reach:'"',acc:"%",def:"%",tdacc:"%",tddef:"%"};
// Estimación a partir de las valoraciones: solo se usa si falta el dato real
const EST=f=>({slpm:+(.1*f.S-2.8).toFixed(1),acc:Math.round(36+.14*f.S),sapm:+(6.2-.035*f.R).toFixed(1),def:Math.round(35+.4*f.R),tdavg:+Math.max(0,(f.G-40)*.06).toFixed(1),tdacc:Math.round(25+.3*f.G),tddef:Math.round(40+.5*f.G),sub:+Math.max(0,(f.B-30)*.025).toFixed(1)});
// [valor, 1 si es dato real | 0 si es estimado]
function sv(f,k){return f[k]!=null?[f[k],1]:(k=="reach"?[null,0]:[EST(f)[k],0])}
// Ajuste extra cuando ambos tienen datos reales: alcance, diferencial de golpes y defensa
function ex(a,b){let d=0;if((a.beat||[]).includes(b.n))d+=10;if((b.beat||[]).includes(a.n))d-=10; // cara a cara previo en la UFC
if(a.reach&&b.reach)d+=.35*(a.reach-b.reach);if(["slpm","sapm","def"].every(k=>a[k]!=null&&b[k]!=null))d+=2*((a.slpm-a.sapm)-(b.slpm-b.sapm))+.05*(a.def-b.def);return d}
const st=f=>.6*f.S+.4*f.P,gr=f=>.6*f.G+.4*f.B,wp=f=>{const[x,y]=f.r.split("-").map(Number);return x/(x+y)};
function sim(a,b){const g=.5+Math.abs(a.G-b.G)/120,sc=f=>g*gr(f)+(1-g)*st(f),tot=f=>.75*sc(f)+.15*f.R+10*wp(f);
const p=1/(1+Math.exp(-(tot(a)-tot(b)+ex(a,b))/14)),ko=(a.P+b.P)/2*(1-g),sb=(a.B+b.B)/2*g*.8,dc=(a.R+b.R)/2*.55,s=ko+sb+dc,ds=st(a)-st(b),dg=gr(a)-gr(b),w=Math.abs(ds)>=Math.abs(dg)?[ds,"e1"]:[dg,"e2"];
return{p,m:[ko,sb,dc].map(x=>Math.round(x/s*100)),who:w[0]>=0?a.n:b.n,ek:w[1]}}
