import {createClient} from 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/+esm';
import {SUPABASE_URL,SUPABASE_PUBLISHABLE_KEY} from './config.js';
const CONFIG={tz:'Asia/Kolkata'};
const Utilities={formatDate(d,tz){const parts=new Intl.DateTimeFormat('en-CA',{timeZone:tz,year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(d);const v=Object.fromEntries(parts.map(p=>[p.type,p.value]));return `${v.year}-${v.month}-${v.day}`}};
let client,session,member;
export async function requireLogin(){
 if(!SUPABASE_PUBLISHABLE_KEY.startsWith('sb_publishable_'))throw Error('Correct project publishable key must be configured before testing.');
 client=createClient(SUPABASE_URL,SUPABASE_PUBLISHABLE_KEY);
 const current=await client.auth.getSession();session=current.data.session;
 if(!session){document.getElementById('login').hidden=false;await new Promise(resolve=>{document.getElementById('loginform').onsubmit=async e=>{e.preventDefault();const f=e.target,b=f.querySelector('button');b.disabled=true;try{const r=await client.auth.signInWithPassword({email:f.email.value.trim(),password:f.password.value});if(r.error)throw r.error;session=r.data.session;f.password.value='';resolve()}catch(err){document.getElementById('loginerror').textContent=err.message}finally{b.disabled=false}}})}
 const r=await client.from('planning_direct_members').select('enabled,role').eq('user_id',session.user.id).single();
 if(r.error||!r.data?.enabled){await client.auth.signOut();throw Error('This operator has not been enabled by the administrator.');}member=r.data;
 document.getElementById('login').hidden=true;
 document.getElementById('logout').hidden=false;
 document.getElementById('logout').onclick=async()=>{await client.auth.signOut();location.reload()};
 client.auth.onAuthStateChange((event)=>{if(event==='SIGNED_OUT'){document.body.inert=true;location.reload()}});
 return session.user.id;
}
async function sql_(path,method='get',body){const s=await client.auth.getSession();if(!s.data.session)throw Error('Login expired. Draft remains on this device.');const r=await fetch(SUPABASE_URL+'/rest/v1/'+path,{method:method.toUpperCase(),headers:{apikey:SUPABASE_PUBLISHABLE_KEY,Authorization:'Bearer '+s.data.session.access_token,'Content-Type':'application/json'},...(body===undefined?{}:{body:JSON.stringify(body)})});const value=await r.json();if(!r.ok)throw Error(value.message||'SQL request failed');return value}
async function all_(table,query){const out=[];for(let offset=0;offset<=100000;offset+=500){const page=await sql_(table+'?select=*&'+query+'&limit=500&offset='+offset);out.push(...page);if(page.length<500)return out}throw Error('Narrow the query');}
function bootstrap(){return {user:{email:session.user.email,views:['MACHINE_NAME']},machines:[],reportMachines:[],today:Utilities.formatDate(new Date(),CONFIG.tz)}}
export function rpc(name,...args){const api={bootstrap,listJobs,saveJob,extendJob};if(!api[name])return Promise.reject(Error('Production Planning is enabled in this isolated test. Reports are not enabled yet.'));return Promise.resolve().then(()=>api[name](...args))}
const BASE_REPORT_MACHINES=['JF MACHINE','SMARTECH','NEW MACHINE','FOLDER & GLUER','AUTO STITCHING','MANUAL PUNCHING','MANUAL STITCHING','MANUAL SLOTTING','MANUAL CREASING','MANUAL PASTING','MANUAL BUNDLING','MANUAL CLEANING','SEMI-AUTO STITCHING'];
function stageOf_(p){p=String(p||'').toUpperCase();if(/CORRUGAT|BOARDLINE/.test(p))return 1;if(/PRINT|SLOT/.test(p))return 2;if(/STRAP|BUNDL/.test(p))return 4;if(/QUALITY|OQC|OUTWARD/.test(p))return 5;return 3;}
async function listJobs(){
 const rows=await all_('production_planning_test','order=source_row.asc,row_id.asc');
 const done=j=>String(j['Input Qty']??'').trim()!==''||['submitted','partial','skipped'].includes(String(j['ERP Status']).toLowerCase())||String(j['Job Status']).toLowerCase()==='closed';
 const min={},route={};for(const r of rows){if(r.erp_closed)continue;const j=r.data,w=j['WO No'],s=stageOf_(j['Process Name']);(route[w]=route[w]||[]).push({s,p:j['Process Name']});if(!done(j))min[w]=Math.min(min[w]||99,s);}
 const today=Utilities.formatDate(new Date(),CONFIG.tz,'yyyy-MM-dd');const cutoff=monthCutoff_(today);
 return rows.filter(r=>!r.erp_closed&&(String(r.data['Job Status']||'').toLowerCase()!=='closed'||isAutoProcess_(r.data['Process Name']))&&String(r.data['ERP Closed']||'').toLowerCase()!=='true'&&Math.max(dateMs_(r.data.Date),dateMs_(r.data['Production Date']))>=cutoff).map(r=>{const j=r.data,s=stageOf_(j['Process Name']),w=j['WO No'];const next=(route[w]||[]).filter(x=>x.s>s).sort((a,b)=>a.s-b.s)[0];return {...j,autoProcess:isAutoProcess_(j['Process Name']),version:String(r.revision),ready:!done(j)&&s===min[w],stage:s,nextProc:next?next.p:''};});
}
function dateMs_(s){s=String(s||'');let m;if((m=s.match(/^(\d{4})-(\d{2})-(\d{2})$/)))return Date.UTC(+m[1],+m[2]-1,+m[3]);if((m=s.match(/^(\d{1,2})-(\d{1,2})-(\d{4})$/)))return Date.UTC(+m[3],+m[2]-1,+m[1]);if((m=s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/)))return Date.UTC(+m[3],+m[1]-1,+m[2]);return 0;}
function number_(v,label,integer){if(v===''||v==null||!Number.isFinite(Number(v))||Number(v)<0||(integer&&!Number.isInteger(Number(v))))throw Error('Enter valid '+label);return Number(v);}
function date_(s){if(!/^\d{4}-\d{2}-\d{2}$/.test(s||''))throw Error('Enter a valid date');const d=new Date(s+'T00:00:00+05:30');if(Utilities.formatDate(d,CONFIG.tz,'yyyy-MM-dd')!==s)throw Error('Invalid date');return s;}
function minutes_(s){if(!/^([01]\d|2[0-3]):[0-5]\d$/.test(s||''))throw Error('Use HH:MM');const a=s.split(':').map(Number);return a[0]*60+a[1];}
function text_(s){s=String(s||'');if(s.length>1000)throw Error('Text too long');return s;}
function mutate_(action,id,version,data,request){if(!/^[a-zA-Z0-9-]{16,64}$/.test(request||''))throw Error('Submission ID required');return sql_('rpc/planning_direct_mutate','post',{p_action:action,p_id:id,p_expected:Number(version||0),p_data:data,p_request:request});}
function jobPatch_(p){minutes_(p.start);minutes_(p.end);const input=number_(p.input,'Input',true),rej=number_(p.rejection,'Rejection',true),prod=number_(p.production,'Production',true);if(rej>input)throw Error('Rejection cannot exceed input');return {'Start Time':p.start,'End Time':p.end,'Input Qty':input,'Rej Qty':rej,'Production Qty':prod,'Production Date':date_(p.date),'Remarks':text_(p.remarks),'Destination':text_(p.destination),'No of Pallets':number_(p.pallets,'Pallets',false)};}
function saveJob(p){return mutate_(p.override==='1'?'override':'save',p.id,p.version,jobPatch_(p),p.reqId);}
function extendJob(p){const patch=jobPatch_(p);if(patch['Production Qty']<=0)throw Error('Production must exceed zero');return mutate_('extend',p.id,p.version,patch,p.reqId);}

function monthCutoff_(today){const [y,m,d]=today.split('-').map(Number);const last=new Date(Date.UTC(y,m-1,0)).getUTCDate();return Date.UTC(y,m-2,Math.min(d,last));}

function isAutoProcess_(name){return /STRAPP?ING|BUNDLING|OUTWARD.*QUALITY|QUALITY.*CHECK|\bOQC\b/i.test(String(name||''));}
