import { useState, useEffect, useRef } from "react"
import {
  MessageSquare, FileText, Settings, Search, Upload, Mic, Send,
  Plus, Sparkles, Brain, Database, Clock, ChevronDown, Shield,
  GitBranch, BookOpen, ArrowRight, Layers, Trash2, CheckCircle, AlertCircle, LogIn, Image
} from "lucide-react"
import DenominationSelector from './components/DenominationSelector'
import ImageGenerator from './components/ImageGenerator'
import ScriptureCard from './components/ScriptureCard'

const API = "http://localhost:8000"

const GLOBAL_CSS = `
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg: #07090f; --surface: #0d1117; --card: #111827;
    --border: rgba(255,255,255,0.07);
    --cyan: #06b6d4; --cyan-dim: rgba(6,182,212,0.12);
    --purple: #8b5cf6; --purple-dim: rgba(139,92,246,0.12);
    --green: #10b981; --amber: #f59e0b; --red: #ef4444;
    --text: #e2e8f0; --text-2: #94a3b8; --text-3: #64748b; --text-4: #334155;
    --ff-display: 'Syne', sans-serif;
    --ff-mono: 'JetBrains Mono', monospace;
    --ff-body: 'Inter', sans-serif;
  }
  body { color: var(--text); font-family: var(--ff-body); overflow:hidden; margin:0; padding:0; }
  ::-webkit-scrollbar { width: 3px; } ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 2px; }

  @keyframes pulse    { 0%,100%{opacity:1} 50%{opacity:.35} }
  @keyframes glow     { 0%,100%{box-shadow:0 0 18px rgba(6,182,212,.2)} 50%{box-shadow:0 0 36px rgba(6,182,212,.45)} }
  @keyframes bounceUp { 0%,80%,100%{transform:translateY(0)} 40%{transform:translateY(-7px)} }
  @keyframes wave     { 0%,100%{height:3px} 50%{height:15px} }
  @keyframes fadeUp   { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:translateY(0)} }
  @keyframes slideR   { from{opacity:0;transform:translateX(16px)} to{opacity:1;transform:translateX(0)} }
  @keyframes fadeIn   { from{opacity:0} to{opacity:1} }
  @keyframes spin     { to{transform:rotate(360deg)} }
  @keyframes progress { from{width:0%} to{width:90%} }

  .nav-btn { transition:all .15s; }
  .nav-btn:hover { background:rgba(255,255,255,.05)!important; }
  .nav-btn.on { background:var(--cyan-dim)!important; color:var(--cyan)!important; }
  .chat-row { transition:background .15s; }
  .chat-row:hover { background:rgba(255,255,255,.04)!important; cursor:pointer; }
  .chat-row.on { background:rgba(255,255,255,.06)!important; }
  .src-card { transition:border-color .2s,transform .2s; }
  .src-card:hover { border-color:rgba(6,182,212,.3)!important; transform:translateY(-1px); }
  .rtab { transition:all .15s; }
  .rtab:hover { color:var(--text-2)!important; }
  .rtab.on { color:var(--cyan)!important; border-bottom:2px solid var(--cyan)!important; }
  .send-btn { transition:all .2s; }
  .send-btn:hover:not(:disabled) { background:#0891b2!important; box-shadow:0 0 28px rgba(6,182,212,.55)!important; }
  .send-btn:active:not(:disabled){ transform:scale(.95); }
  .iarea:focus-within { border-color:rgba(6,182,212,.35)!important; box-shadow:0 0 0 1px rgba(6,182,212,.08),0 0 28px rgba(6,182,212,.06)!important; }
  .cite { transition:background .15s; }
  .cite:hover { background:rgba(6,182,212,.28)!important; cursor:pointer; }
  .kb-chip { transition:all .15s; }
  .kb-chip:hover { border-color:rgba(139,92,246,.4)!important; }
  .kb-chip.on { background:var(--purple-dim)!important; border-color:var(--purple)!important; color:var(--purple)!important; }
  .drop-zone { transition:all .2s; }
  .drop-zone:hover { border-color:rgba(6,182,212,.4)!important; background:rgba(6,182,212,.03)!important; cursor:pointer; }
  .drop-zone.drag { border-color:var(--cyan)!important; background:rgba(6,182,212,.07)!important; animation:glow 1s ease infinite; }
  .icon-btn { transition:all .15s; }
  .icon-btn:hover { background:rgba(255,255,255,.07)!important; color:var(--text-2)!important; }
  .cmd-item:hover { background:rgba(255,255,255,.06)!important; cursor:pointer; }
  .expand-btn { transition:all .15s; }
  .expand-btn:hover { color:var(--cyan)!important; border-color:rgba(6,182,212,.25)!important; }
  .sug-btn { transition:all .15s; }
  .sug-btn:hover { border-color:rgba(6,182,212,.3)!important; color:var(--text-2)!important; }
  .doc-row:hover .del-btn { opacity:1!important; }
  .del-btn { transition:all .15s; opacity:0; }
  .del-btn:hover { color:#ef4444!important; }
`

const glass = { background:'rgba(255,255,255,0.025)', border:'1px solid rgba(255,255,255,0.07)', backdropFilter:'blur(20px)' }
const DOC_COLORS = ['#06b6d4','#8b5cf6','#10b981','#f59e0b','#ef4444','#ec4899']
const CMD = [
  { icon:'💬', label:'New conversation', key:'N' },
  { icon:'📄', label:'Upload document',  key:'U' },
  { icon:'🔍', label:'Search documents', key:'F' },
  { icon:'🧠', label:'View memory',      key:'M' },
  { icon:'⚙️', label:'Open settings',   key:',' },
]
const MEMORY = [
  { id:1, icon:'🧠', text:'User is building a RAG system with FAISS + Groq', ts:'This session' },
  { id:2, icon:'⚙️', text:'Project uses React + FastAPI stack',               ts:'This session' },
  { id:3, icon:'📄', text:'Multi-PDF support recently implemented',            ts:'This session' },
  { id:4, icon:'✂️', text:'User prefers minimal, surgical code changes',       ts:'This session' },
]
const SUGGESTIONS = ['Summarize all uploaded documents','What are the key differences?','List the main topics covered']
const FAITH_SUGGESTIONS = ['What does John 3:16 say?','Summarize the Beatitudes','When was the Council of Nicaea?','What is the Book of Tobit?']

export default function RAGInterface() {
  const [msgs, setMsgs]                 = useState([])
  const [inp, setInp]                   = useState('')
  const [rtab, setRtab]                 = useState('sources')
  const [nav, setNav]                   = useState('chat')
  const [streaming, setStream]          = useState(false)
  const [cmdOpen, setCmd]               = useState(false)
  const [rOpen, setROpen]               = useState(true)
  const [voice, setVoice]               = useState(false)
  const [drag, setDrag]                 = useState(false)
  const [sourceFilter, setFilter]       = useState('all')
  const [expanded, setExpanded]         = useState(null)
  const [docs, setDocs]                 = useState([])
  const [latestSources, setLatestSrc]   = useState([])
  const [uploading, setUploading]       = useState(null)
  const [toast, setToast]               = useState(null)
  const [token, setToken]               = useState(localStorage.getItem('token') || null)
  const [loginUser, setLoginUser]       = useState('')
  const [loginPass, setLoginPass]       = useState('')
  const [loginErr, setLoginErr]         = useState('')
  const [loginLoading, setLoginLoading] = useState(false)
  const [denomination, setDenomination] = useState('general')
  const endRef   = useRef(null)
  const fileRef  = useRef(null)
  const msgsRef  = useRef(null)

  const authHeaders = useCallback(() => token ? { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' } : {}, [token])

  const handleLogin = async () => {
    setLoginLoading(true); setLoginErr('')
    try {
      const r = await fetch(`${API}/login`, {
        method:'POST', headers:{'Content-Type':'application/json'},
        body:JSON.stringify({ username: loginUser, password: loginPass }),
      })
      const d = await r.json()
      if (d.token) {
        localStorage.setItem('token', d.token)
        setToken(d.token)
        setLoginUser(''); setLoginPass('')
      } else {
        setLoginErr(d.detail || 'Login failed')
      }
    } catch { setLoginErr('Cannot reach backend') }
    setLoginLoading(false)
  }

  useEffect(() => {
    if (!token) return
    fetch(`${API}/sources`, { headers: authHeaders() }).then(r=>r.json()).then(d=>{ if(d.sources) syncDocs(d.sources) }).catch(()=>{})
  }, [token, authHeaders])

  useEffect(() => {
    const fn = e => {
      if ((e.metaKey||e.ctrlKey) && e.key==='k') { e.preventDefault(); setCmd(p=>!p) }
      if (e.key==='Escape') setCmd(false)
    }
    window.addEventListener('keydown', fn)
    return () => window.removeEventListener('keydown', fn)
  }, [])

  // const isFirstRender = useRef(true);

  useEffect(() => {
    if (msgs.length > 0 && msgsRef.current) {
      msgsRef.current.scrollTop = msgsRef.current.scrollHeight
    }
  }, [msgs, streaming])

// useEffect(() => {
//   document.documentElement.scrollTop = 0;
//   document.body.scrollTop = 0;
// }, []); // ← empty array = sirf refresh/mount pe chalega

  useEffect(() => {
    if (!toast) return
    const t = setTimeout(() => setToast(null), 3500)
    return () => clearTimeout(t)
  }, [toast])

  const syncDocs = sources => setDocs(sources.map((name,i) => ({ name, color: DOC_COLORS[i%DOC_COLORS.length], chunks:null })))
  const showToast = (msg, type='success') => setToast({msg,type})

  const uploadFile = async files => {
    if (!files || files.length === 0) { showToast('No files selected.','error'); return }
    const supported = ['.pdf', '.csv', '.json']
    const valid = Array.from(files).filter(f => supported.includes(f.name.toLowerCase().slice(f.name.lastIndexOf('.'))))
    if (valid.length === 0) { showToast('Only PDF, CSV, and JSON files are supported.','error'); return }
    if (valid.length !== files.length) { showToast('Skipped unsupported files.','error') }
    setUploading(`${valid.length} file(s)`); setRtab('docs')
    let totalChunks = 0
    let successCount = 0
    for (const file of valid) {
      const form = new FormData()
      form.append('file', file)
      try {
        const headers = { 'Authorization': `Bearer ${token}` }
        const res  = await fetch(`${API}/upload`, { method:'POST', body:form, headers })
        const data = await res.json()
        if (data.error) {
          showToast(data.error,'error')
        } else {
          syncDocs(data.all_sources)
          setDocs(prev => prev.map(d => d.name===data.filename ? {...d, chunks:data.chunks} : d))
          totalChunks += data.chunks
          successCount++
        }
      } catch { showToast('Upload failed — is the backend running?','error') }
    }
    if (successCount > 0) { showToast(`✅ Indexed ${totalChunks} chunks from ${successCount} file(s)`) }
    setUploading(null)
  }

  const deletePDF = async filename => {
    try {
      const res  = await fetch(`${API}/sources/${encodeURIComponent(filename)}`, {method:'DELETE', headers: authHeaders()})
      const data = await res.json()
      if (res.status === 403) { showToast('Access denied — admin only','error'); return }
      syncDocs(data.remaining_sources)
      if (sourceFilter===filename) setFilter('all')
      showToast(`Removed ${filename}`)
    } catch { showToast('Delete failed.','error') }
  }

  const send = async () => {
    if (!inp.trim()||streaming) return
    const question = inp.trim()
    const ts = new Date().toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'})
    setMsgs(p=>[...p,{id:Date.now(),role:'user',ts,content:question}])
    setInp(''); setStream(true); setLatestSrc([])
    try {
      const res  = await fetch(`${API}/christianity/query`,{
        method:'POST', headers:{'Content-Type':'application/json', ...authHeaders()},
        body:JSON.stringify({
          query: question,
          denomination: denomination,
          source_filter: sourceFilter==='all'?null:sourceFilter,
        }),
      })
      const data = await res.json()
      if (data.error) {
        setMsgs(p=>[...p,{id:Date.now()+1,role:'ai',ts,content:data.error,sources:[],conf:0}])
      } else {
        const sources = data.sources||[]
        const refs = data.verified_refs||[]
        setLatestSrc(sources)
        setMsgs(p=>[...p,{
          id:Date.now()+1, role:'ai', ts, content:data.answer, sources,
          verifiedRefs: refs,
          conf: sources.length > 0 ? 85 : (refs.length > 0 ? 95 : 0),
          reasoning:[
            `Denomination: ${data.denomination||denomination}`,
            refs.length > 0 ? `Verified ${refs.length} scripture reference(s) from KJV` : 'No scripture references detected',
            sources.length > 0 ? `Retrieved ${sources.length} source(s)` : 'No document sources',
            'LLM generated with grounded context',
          ],
        }])
        if(sources.length>0) setRtab('sources')
      }
    } catch {
      setMsgs(p=>[...p,{id:Date.now()+1,role:'ai',ts,content:'Failed to reach backend. Make sure `uvicorn api:app --reload --port 8000` is running.',sources:[],conf:0}])
    } finally { setStream(false) }
  }

  const parseContent = txt =>
    (txt||'').replace(/\*\*(.*?)\*\*/g,'<strong style="color:#e2e8f0;font-weight:600">$1</strong>')
             .replace(/\[([¹²³\d]+)\]/g,'<span class="cite" style="display:inline-flex;align-items:center;padding:1px 6px;margin:0 2px;border-radius:4px;background:rgba(6,182,212,.12);border:1px solid rgba(6,182,212,.25);color:#06b6d4;font-size:10px;font-family:JetBrains Mono,monospace;">$1</span>')

  const hasIndex = docs.length > 0

  if (!token) return (
    <div style={{
      display:'flex', height:'100vh', background:'#07090f',
      alignItems:'center', justifyContent:'center',
      fontFamily:'Inter,sans-serif', flexDirection:'column', gap:24
    }}>
      <div style={{position:'absolute',inset:0,pointerEvents:'none',zIndex:0,
        backgroundImage:'linear-gradient(rgba(6,182,212,.025) 1px,transparent 1px),linear-gradient(90deg,rgba(6,182,212,.025) 1px,transparent 1px)',backgroundSize:'44px 44px'}}/>
      <div style={{width:52,height:52,borderRadius:14,
        background:'linear-gradient(135deg,#06b6d4,#8b5cf6)',
        display:'flex',alignItems:'center',justifyContent:'center',
        boxShadow:'0 0 32px rgba(6,182,212,.35)',fontSize:22,fontWeight:800,color:'#fff',fontFamily:'Syne,sans-serif'}}>R</div>
      <div style={{textAlign:'center'}}>
        <div style={{fontSize:20,fontWeight:700,color:'#cbd5e1',fontFamily:'Syne,sans-serif',marginBottom:4}}>RAG Assistant</div>
        <div style={{fontSize:12,color:'#475569'}}>Sign in to access your documents</div>
      </div>
      <div style={{width:300,display:'flex',flexDirection:'column',gap:10}}>
        <input value={loginUser} onChange={e=>setLoginUser(e.target.value)}
          placeholder="Username" onKeyDown={e=>e.key==='Enter'&&handleLogin()}
          style={{padding:'10px 14px',borderRadius:8,border:'1px solid rgba(255,255,255,.1)',
            background:'rgba(255,255,255,.04)',color:'#e2e8f0',fontSize:13,fontFamily:'Inter,sans-serif',outline:'none'}}/>
        <input value={loginPass} onChange={e=>setLoginPass(e.target.value)}
          type="password" placeholder="Password" onKeyDown={e=>e.key==='Enter'&&handleLogin()}
          style={{padding:'10px 14px',borderRadius:8,border:'1px solid rgba(255,255,255,.1)',
            background:'rgba(255,255,255,.04)',color:'#e2e8f0',fontSize:13,fontFamily:'Inter,sans-serif',outline:'none'}}/>
        <button onClick={handleLogin} disabled={loginLoading||!loginUser||!loginPass}
          style={{width:'100%',padding:'10px',borderRadius:8,border:'none',
            background:loginLoading?'#1e2736':'#06b6d4',color:loginLoading?'#475569':'#fff',
            fontSize:13,fontWeight:600,cursor:loginLoading?'not-allowed':'pointer',
            fontFamily:'Inter,sans-serif',display:'flex',alignItems:'center',justifyContent:'center',gap:8}}>
          {loginLoading ? <span style={{animation:'spin .7s linear infinite',display:'inline-block'}}>⟳</span> : <LogIn size={14}/>}
          {loginLoading ? 'Signing in…' : 'Sign in'}
        </button>
        {loginErr && <div style={{fontSize:12,color:'#ef4444',textAlign:'center'}}>{loginErr}</div>}
      </div>
      <div style={{fontSize:10,color:'#1e293b',textAlign:'center'}}>Default: <strong style={{color:'#334155'}}>admin</strong> / <strong style={{color:'#334155'}}>admin123</strong></div>
      <style>{GLOBAL_CSS}</style>
    </div>
  )

  return (
  <div style={{
        
        display:'flex', height:'100vh', background:'#07090f',
        overflow:'hidden', overscrollBehavior:'none', fontFamily:'Inter,sans-serif',
        
        
      
      boxShadow:'0 0 40px rgba(6,182,212,0.08), inset 0 0 0 1px rgba(255,255,255,0.04)'
    }}>
      <style>{GLOBAL_CSS}</style>

      {/* Grid bg */}
      <div style={{position:'absolute',inset:0,pointerEvents:'none',zIndex:0,
        backgroundImage:'linear-gradient(rgba(6,182,212,.025) 1px,transparent 1px),linear-gradient(90deg,rgba(6,182,212,.025) 1px,transparent 1px)',backgroundSize:'44px 44px'}}/>
      <div style={{position:'absolute',top:'-180px',left:'35%',width:'580px',height:'380px',
        background:'radial-gradient(ellipse,rgba(6,182,212,.07) 0%,transparent 68%)',pointerEvents:'none',zIndex:0}}/>
      <div style={{position:'absolute',bottom:'-100px',right:'20%',width:'400px',height:'300px',
        background:'radial-gradient(ellipse,rgba(139,92,246,.05) 0%,transparent 68%)',pointerEvents:'none',zIndex:0}}/>

      {/* Toast */}
      {toast&&(
        <div style={{position:'fixed',top:18,left:'50%',transform:'translateX(-50%)',zIndex:200,
          padding:'9px 18px',borderRadius:10,fontSize:12,fontWeight:500,
          background:toast.type==='error'?'rgba(239,68,68,.15)':'rgba(16,185,129,.12)',
          border:`1px solid ${toast.type==='error'?'rgba(239,68,68,.35)':'rgba(16,185,129,.3)'}`,
          color:toast.type==='error'?'#ef4444':'#10b981',
          boxShadow:'0 8px 32px rgba(0,0,0,.4)',backdropFilter:'blur(16px)',
          display:'flex',alignItems:'center',gap:8,animation:'fadeUp .2s ease',whiteSpace:'nowrap'}}>
          {toast.type==='error'?<AlertCircle size={13}/>:<CheckCircle size={13}/>}{toast.msg}
        </div>
      )}

      {/* ── LEFT SIDEBAR ── */}
      <aside style={{
          width:232,
          flexShrink:0,
          display:'flex',
          flexDirection:'column',
          height:'100vh',
          overflow:'hidden',
          borderRight:'1px solid rgba(255,255,255,0.06)',
          background:'rgba(7,9,15,0.85)',
          backdropFilter:'blur(24px)',
          zIndex:10
        }}>

        {/* Logo */}
        <div style={{padding:'28px 14px 14px',borderBottom:'1px solid rgba(255,255,255,0.06)'}}>
          <div style={{display:'flex',alignItems:'center',gap:10}}>
            <div style={{width:34,height:34,borderRadius:9,background:'linear-gradient(135deg,#06b6d4,#8b5cf6)',
              display:'flex',alignItems:'center',justifyContent:'center',boxShadow:'0 0 22px rgba(6,182,212,.35)',
              fontSize:15,fontWeight:800,color:'#fff',fontFamily:'Syne,sans-serif'}}>R</div>
            <div>
              <div style={{fontSize:14,fontWeight:700,color:'#e2e8f0',fontFamily:'Syne,sans-serif',letterSpacing:'-.3px'}}>RAG Assistant</div>
              <div style={{fontSize:10,color:'#06b6d4',fontFamily:'JetBrains Mono,monospace',marginTop:1}}>v2.0 · multi-pdf</div>
            </div>
          </div>
        </div>

        {/* Nav */}
        <div style={{padding:'10px 8px',display:'flex',flexDirection:'column',gap:2}}>
          {[{id:'chat',icon:MessageSquare,label:'Conversations'},{id:'documents',icon:FileText,label:'Documents'},{id:'settings',icon:Settings,label:'Settings'}]
            .map(({id,icon:I,label})=>(
            <button key={id} className={`nav-btn${nav===id?' on':''}`} onClick={()=>setNav(id)}
              style={{display:'flex',alignItems:'center',gap:9,padding:'8px 11px',borderRadius:8,
                border:'none',cursor:'pointer',background:'transparent',
                color:nav===id?'#06b6d4':'#64748b',fontSize:13,fontWeight:500,width:'100%',fontFamily:'Inter,sans-serif'}}>
              <I size={14}/>{label}
            </button>
          ))}
          <button onClick={()=>{localStorage.removeItem('token');setToken(null)}}
            style={{display:'flex',alignItems:'center',gap:9,padding:'8px 11px',borderRadius:8,
              border:'none',cursor:'pointer',background:'transparent',color:'#475569',fontSize:11,width:'100%',fontFamily:'Inter,sans-serif',marginTop:4}}>
            <LogIn size={13} style={{transform:'rotate(180deg)'}}/>Sign out
          </button>
        </div>

        {/* Source filter */}
        <div style={{padding:'6px 12px 10px'}}>
          <div style={{fontSize:10,color:'#475569',textTransform:'uppercase',letterSpacing:'.08em',fontWeight:600,marginBottom:7}}>Filter Source</div>
          {['all',...docs.map(d=>d.name)].map(src=>(
            <div key={src} style={{display:'flex',alignItems:'center',marginBottom:3}}>
              <button className={`kb-chip${sourceFilter===src?' on':''}`} onClick={()=>setFilter(src)}
                style={{display:'flex',alignItems:'center',gap:6,flex:1,padding:'6px 9px',borderRadius:6,
                  border:'1px solid rgba(255,255,255,0.07)',background:'transparent',color:'#94a3b8',
                  fontSize:11,cursor:'pointer',fontFamily:'JetBrains Mono,monospace',textAlign:'left',
                  overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>
                <Database size={10}/>{src==='all'?'All documents':src}
              </button>
              {src!=='all'&&(
                <button onClick={()=>deletePDF(src)}
                  style={{padding:4,marginLeft:4,borderRadius:4,border:'none',background:'rgba(239,68,68,.1)',color:'#ef4444',cursor:'pointer'}}>
                  <Trash2 size={10}/>
                </button>
              )}
            </div>
          ))}
        </div>

        {/* Recent chats */}
        <div style={{flex:1,display:'flex',flexDirection:'column',overflow:'hidden'}}>
          <div style={{padding:'0 14px 7px',display:'flex',alignItems:'center',justifyContent:'space-between'}}>
            <span style={{fontSize:10,color:'#475569',textTransform:'uppercase',letterSpacing:'.08em',fontWeight:600}}>Recent</span>
            <button onClick={()=>setMsgs([])} style={{background:'none',border:'none',cursor:'pointer',color:'#475569',borderRadius:4,padding:2}}><Plus size={11}/></button>
          </div>
          <div style={{flex:1,overflowY:'auto',padding:'0 8px'}}>
            {msgs.filter(m=>m.role==='user').slice(-6).reverse().map((m,i)=>(
              <div key={m.id} className={`chat-row${i===0?' on':''}`}
                style={{padding:'7px 10px',borderRadius:7,marginBottom:2,display:'flex',alignItems:'center',gap:7,
                  background:i===0?'rgba(255,255,255,.06)':'transparent'}}>
                <MessageSquare size={10} color="#475569" style={{flexShrink:0}}/>
                <span style={{fontSize:12,color:i===0?'#cbd5e1':'#64748b',overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{m.content}</span>
              </div>
            ))}
            {msgs.filter(m=>m.role==='user').length===0&&(
              <div style={{padding:'8px 10px',fontSize:11,color:'#334155'}}>No conversations yet.</div>
            )}
          </div>
        </div>

        {/* ⌘K */}
        <div style={{padding:'10px 12px',borderTop:'1px solid rgba(255,255,255,0.06)'}}>
          <button onClick={()=>setCmd(true)} style={{width:'100%',padding:'7px 10px',borderRadius:7,
            border:'1px solid rgba(255,255,255,0.07)',background:'rgba(255,255,255,.02)',
            color:'#475569',fontSize:11,cursor:'pointer',display:'flex',alignItems:'center',justifyContent:'space-between',fontFamily:'Inter,sans-serif'}}>
            <div style={{display:'flex',alignItems:'center',gap:6}}><Search size={10}/><span>Command palette</span></div>
            <kbd style={{fontFamily:'JetBrains Mono,monospace',fontSize:9,color:'#334155',background:'rgba(255,255,255,.05)',padding:'2px 5px',borderRadius:3,border:'1px solid rgba(255,255,255,.08)'}}>⌘K</kbd>
          </button>
        </div>
      </aside>

      {/* ── MAIN ── */}
      <main style={{flex:1,height:'100%',display:'flex',flexDirection:'column',overflow:'hidden',overscrollBehavior:'contain',position:'relative',zIndex:5}}>

        {/* Header */}
        <div style={{padding:'23px 22px 13px',borderBottom:'1px solid rgba(255,255,255,0.06)',
          display:'flex',alignItems:'center',justifyContent:'space-between',
          background:'rgba(7,9,15,.7)',backdropFilter:'blur(20px)',flexShrink:0}}>
          <div>
            <div style={{fontSize:14,fontWeight:700,color:'#e2e8f0',fontFamily:'Syne,sans-serif'}}>
              {msgs.length>0?(msgs.find(m=>m.role==='user')?.content?.slice(0,42)+'…'):'New conversation'}
            </div>
            <div style={{display:'flex',alignItems:'center',gap:8,marginTop:2}}>
              <span style={{fontSize:11,color:'#475569'}}>{docs.length} doc{docs.length!==1?'s':''} indexed</span>
              <span style={{width:3,height:3,borderRadius:'50%',background:'#334155'}}/>
              <span style={{fontSize:11,color:hasIndex?'#06b6d4':'#475569',display:'flex',alignItems:'center',gap:5}}>
                <span style={{width:6,height:6,borderRadius:'50%',background:hasIndex?'#06b6d4':'#475569',
                  display:'inline-block',animation:hasIndex?'pulse 2s ease infinite':''}}/>
                {hasIndex?`${sourceFilter==='all'?'all docs':sourceFilter} active`:'no docs'}
              </span>
            </div>
          </div>
          <button className="icon-btn" onClick={()=>setROpen(p=>!p)}
            style={{width:32,height:32,borderRadius:7,...glass,border:'1px solid rgba(255,255,255,.07)',
              cursor:'pointer',color:'#64748b',display:'flex',alignItems:'center',justifyContent:'center',flexShrink:0}}>
            <Layers size={13}/>
          </button>
        </div>

        {/* Empty state */}
        {msgs.length===0&&!streaming&&(
          <div style={{flex:1,display:'flex',flexDirection:'column',alignItems:'center',justifyContent:'center',gap:16,padding:32}}>
            <div style={{width:56,height:56,borderRadius:16,
              background:'linear-gradient(135deg,rgba(6,182,212,.15),rgba(139,92,246,.1))',
              border:'1px solid rgba(6,182,212,.2)',display:'flex',alignItems:'center',justifyContent:'center',
              boxShadow:'0 0 32px rgba(6,182,212,.12)'}}>
              <Sparkles size={24} color="#06b6d4"/>
            </div>
              <div style={{textAlign:'center'}}>
              <div style={{fontSize:18,fontWeight:700,color:'#cbd5e1',fontFamily:'Syne,sans-serif',marginBottom:6}}>
                Christian Theology Assistant
              </div>
              <div style={{fontSize:13,color:'#475569',maxWidth:340}}>
                Ask about scripture, theology, church history, or upload documents for custom RAG queries.
              </div>
            </div>
              <div style={{display:'flex',gap:8,flexWrap:'wrap',justifyContent:'center'}}>
              {(hasIndex ? [...FAITH_SUGGESTIONS, ...SUGGESTIONS] : FAITH_SUGGESTIONS).map((s,i)=>(
                  <button key={i} className="sug-btn" onClick={()=>setInp(s)}
                    style={{padding:'7px 14px',borderRadius:20,fontSize:12,
                      border:'1px solid rgba(255,255,255,.08)',background:'rgba(255,255,255,.02)',
                      color:'#64748b',cursor:'pointer',fontFamily:'Inter,sans-serif',display:'flex',alignItems:'center',gap:5}}>
                    <ArrowRight size={10}/>{s}
                  </button>
                ))}
              </div>
            </div>
          )}

        {/* Messages */}
        <div ref={msgsRef} style={{flex:1,minHeight:0,overflowY:'auto',overscrollBehavior:'contain',padding:'22px',display:'flex',flexDirection:'column',gap:20}}>
          {msgs.map((m,idx)=>(
            <div key={m.id} style={{display:'flex',flexDirection:'column',
              alignItems:m.role==='user'?'flex-end':'flex-start',
              animation:'fadeUp .3s ease both',animationDelay:`${idx*.04}s`}}>

              {m.role==='user'?(
                <div style={{maxWidth:'62%',padding:'12px 16px',borderRadius:'16px 16px 4px 16px',
                  background:'linear-gradient(135deg,rgba(6,182,212,.14),rgba(139,92,246,.09))',
                  border:'1px solid rgba(6,182,212,.2)',color:'#e2e8f0',fontSize:14,lineHeight:1.65}}>
                  {m.content}
                  <div style={{fontSize:10,color:'#475569',marginTop:6,textAlign:'right'}}>{m.ts}</div>
                </div>
              ):(
                <div style={{maxWidth:'78%',display:'flex',flexDirection:'column',gap:7}}>
                  <div style={{display:'flex',alignItems:'center',gap:8}}>
                    <div style={{width:26,height:26,borderRadius:7,flexShrink:0,
                      background:'linear-gradient(135deg,#06b6d4,#8b5cf6)',
                      display:'flex',alignItems:'center',justifyContent:'center',
                      boxShadow:'0 0 14px rgba(6,182,212,.3)'}}>
                      <Sparkles size={12} color="#fff"/>
                    </div>
                    <span style={{fontSize:12,fontWeight:700,color:'#94a3b8',fontFamily:'Syne,sans-serif'}}>RAG Assistant</span>
                    {m.conf>0&&(
                      <div style={{padding:'2px 8px',borderRadius:20,
                        background:m.conf>=90?'rgba(16,185,129,.1)':'rgba(245,158,11,.1)',
                        border:`1px solid ${m.conf>=90?'rgba(16,185,129,.3)':'rgba(245,158,11,.3)'}`,
                        fontSize:10,color:m.conf>=90?'#10b981':'#f59e0b',
                        display:'flex',alignItems:'center',gap:4,fontFamily:'JetBrains Mono,monospace'}}>
                        <Shield size={9}/>{m.conf}% similarity
                      </div>
                    )}
                  </div>
                  <div style={{padding:'14px 16px',borderRadius:'4px 16px 16px 16px',
                    background:'rgba(255,255,255,.03)',border:'1px solid rgba(255,255,255,.07)',
                    color:'#cbd5e1',fontSize:14,lineHeight:1.72}}>
                    {(m.content||'').split('\n\n').map((p,pi,arr)=>(
                      <p key={pi} style={{marginBottom:pi<arr.length-1?12:0}}
                        dangerouslySetInnerHTML={{__html:parseContent(p)}}/>
                    ))}
                    {m.verifiedRefs&&m.verifiedRefs.length>0&&(
                      <div style={{marginTop:12}}>
                        <div style={{fontSize:10,color:'#475569',textTransform:'uppercase',letterSpacing:'.06em',fontWeight:600,marginBottom:6}}>
                          Verified Scripture
                        </div>
                        {m.verifiedRefs
                          .filter(ref => m.content && m.content.includes(ref.reference))
                          .slice(0, 3)
                          .map((ref,i)=>(
                          <ScriptureCard key={i} reference={ref.reference} text={ref.text} verified={true} />
                        ))}
                      </div>
                    )}
                    {m.reasoning&&(
                      <button className="expand-btn" onClick={()=>setExpanded(expanded===m.id?null:m.id)}
                        style={{display:'flex',alignItems:'center',gap:6,marginTop:12,
                          padding:'5px 10px',borderRadius:6,border:'1px solid rgba(255,255,255,.07)',
                          background:'rgba(255,255,255,.02)',color:'#475569',fontSize:11,
                          cursor:'pointer',fontFamily:'Inter,sans-serif'}}>
                        <GitBranch size={11}/>How this was generated
                        <ChevronDown size={11} style={{transform:expanded===m.id?'rotate(180deg)':'rotate(0)',transition:'transform .2s'}}/>
                      </button>
                    )}
                    {expanded===m.id&&m.reasoning&&(
                      <div style={{marginTop:8,padding:'10px 12px',borderRadius:8,
                        background:'rgba(139,92,246,.05)',border:'1px solid rgba(139,92,246,.15)',
                        display:'flex',flexDirection:'column',gap:7}}>
                        {m.reasoning.map((step,si)=>(
                          <div key={si} style={{display:'flex',alignItems:'center',gap:9,
                            animation:'fadeUp .25s ease both',animationDelay:`${si*.07}s`}}>
                            <div style={{width:18,height:18,borderRadius:'50%',flexShrink:0,
                              background:'rgba(139,92,246,.18)',border:'1px solid rgba(139,92,246,.3)',
                              display:'flex',alignItems:'center',justifyContent:'center',
                              fontSize:9,color:'#8b5cf6',fontWeight:700}}>{si+1}</div>
                            <span style={{fontSize:11,color:'#94a3b8'}}>{step}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  <div style={{fontSize:10,color:'#2d3748',paddingLeft:4}}>{m.ts}</div>
                </div>
              )}
            </div>
          ))}

          {/* Streaming */}
          {streaming&&(
            <div style={{display:'flex',flexDirection:'column',alignItems:'flex-start',gap:8,animation:'fadeIn .3s ease'}}>
              <div style={{display:'flex',alignItems:'center',gap:8}}>
                <div style={{width:26,height:26,borderRadius:7,background:'linear-gradient(135deg,#06b6d4,#8b5cf6)',
                  display:'flex',alignItems:'center',justifyContent:'center',animation:'glow 1s ease infinite'}}>
                  <Sparkles size={12} color="#fff"/>
                </div>
                <span style={{fontSize:12,fontWeight:700,color:'#94a3b8',fontFamily:'Syne,sans-serif'}}>Thinking…</span>
              </div>
              <div style={{padding:'13px 16px',borderRadius:'4px 16px 16px 16px',
                background:'rgba(255,255,255,.03)',border:'1px solid rgba(255,255,255,.07)',
                display:'flex',alignItems:'center',gap:5}}>
                {[0,1,2].map(i=>(
                  <div key={i} style={{width:6,height:6,borderRadius:'50%',background:'#06b6d4',
                    animation:'bounceUp 1.2s ease infinite',animationDelay:`${i*.15}s`}}/>
                ))}
              </div>
            </div>
          )}
          <div ref={endRef}/>
        </div>

        {/* Input */}
        <div style={{padding:'14px 22px 18px',background:'rgba(7,9,15,.85)',
          backdropFilter:'blur(20px)',borderTop:'1px solid rgba(255,255,255,.06)',flexShrink:0}}>
          {hasIndex&&msgs.length>0&&(
            <div style={{display:'flex',gap:6,marginBottom:9,flexWrap:'wrap'}}>
              {SUGGESTIONS.map((s,i)=>(
                <button key={i} className="sug-btn" onClick={()=>setInp(s)}
                  style={{padding:'4px 10px',borderRadius:20,fontSize:11,
                    border:'1px solid rgba(255,255,255,.08)',background:'rgba(255,255,255,.02)',
                    color:'#64748b',cursor:'pointer',fontFamily:'Inter,sans-serif',display:'flex',alignItems:'center',gap:5}}>
                  <ArrowRight size={9}/>{s}
                </button>
              ))}
            </div>
          )}
          <div className="iarea" style={{display:'flex',alignItems:'flex-end',gap:6,
            padding:'8px 8px 8px 14px',borderRadius:13,...glass,
            border:'1px solid rgba(255,255,255,.09)',transition:'all .2s'}}>
            <textarea value={inp} onChange={e=>setInp(e.target.value)}
              onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send()}}}
              placeholder={'Ask about scripture, theology, or your documents…'}
              rows={1}
              style={{flex:1,background:'none',border:'none',outline:'none',
                color:'#e2e8f0',fontSize:14,lineHeight:1.5,resize:'none',
                fontFamily:'Inter,sans-serif',maxHeight:110,overflowY:'auto'}}/>
            <div style={{display:'flex',alignItems:'center',gap:3,flexShrink:0}}>
              <button className="icon-btn" onClick={()=>setVoice(p=>!p)}
                style={{width:32,height:32,borderRadius:8,border:'none',cursor:'pointer',
                  background:voice?'rgba(239,68,68,.12)':'transparent',color:voice?'#ef4444':'#475569',
                  display:'flex',alignItems:'center',justifyContent:'center'}}>
                {voice?(
                  <div style={{display:'flex',alignItems:'center',gap:1.5}}>
                    {[1,2,3,2,1].map((h,i)=>(
                      <div key={i} style={{width:2.5,borderRadius:2,background:'#ef4444',
                        animation:'wave .6s ease infinite',animationDelay:`${i*.1}s`,height:h*4}}/>
                    ))}
                  </div>
                ):<Mic size={13}/>}
              </button>

              <input ref={fileRef} type="file" accept=".pdf,.csv,.json" multiple style={{display:'none'}}
                onChange={e=>{if(e.target.files[0])uploadFile(e.target.files);e.target.value=''}}/>
              <button className="icon-btn" onClick={()=>fileRef.current?.click()}
                style={{width:32,height:32,borderRadius:8,border:'none',cursor:'pointer',
                  background:'transparent',color:'#475569',display:'flex',alignItems:'center',justifyContent:'center'}}>
                <Upload size={13}/>
              </button>

              <button className="send-btn" onClick={send} disabled={!inp.trim()||streaming}
                style={{width:34,height:34,borderRadius:9,border:'none',
                  cursor:(inp.trim()&&!streaming)?'pointer':'not-allowed',
                  background:(inp.trim()&&!streaming)?'#06b6d4':'#1e2736',
                  display:'flex',alignItems:'center',justifyContent:'center',
                  boxShadow:inp.trim()?'0 0 20px rgba(6,182,212,.3)':'none'}}>
                <Send size={13} color={(inp.trim()&&!streaming)?'#fff':'#475569'}/>
              </button>
            </div>
          </div>
          <div style={{marginTop:7,fontSize:10,color:'#1e293b',textAlign:'center'}}>
            Scripture-grounded answers · KJV verified ·&nbsp;
            <span style={{color:'#334155'}}>Shift+Enter</span> for newline ·&nbsp;
            <span style={{color:'#334155'}}>⌘K</span> for commands
          </div>
        </div>
      </main>

      {/* ── RIGHT PANEL ── */}
      {rOpen&&(
        <aside style={{width:292,flexShrink:0,display:'flex',flexDirection:'column',
          borderLeft:'1px solid rgba(255,255,255,.06)',
          background:'rgba(7,9,15,.75)',backdropFilter:'blur(24px)',zIndex:10,animation:'slideR .25s ease'}}>

          <div style={{display:'flex',borderBottom:'1px solid rgba(255,255,255,.06)',padding:'0 4px',flexShrink:0}}>
            {[{id:'sources',icon:BookOpen,label:'Sources'},{id:'memory',icon:Brain,label:'Memory'},{id:'docs',icon:FileText,label:'Docs'},{id:'image',icon:Image,label:'Image'}]
              .map(({id,icon:I,label})=>(
              <button key={id} className={`rtab${rtab===id?' on':''}`} onClick={()=>setRtab(id)}
                style={{flex:1,padding:'11px 0',border:'none',background:'none',cursor:'pointer',
                  fontSize:12,fontWeight:500,color:rtab===id?'#06b6d4':'#475569',
                  borderBottom:rtab===id?'2px solid #06b6d4':'2px solid transparent',
                  display:'flex',alignItems:'center',justifyContent:'center',gap:5,fontFamily:'Inter,sans-serif'}}>
                <I size={11}/>{label}
              </button>
            ))}
          </div>

          <div style={{padding:'10px 12px',flexShrink:0}}>
            <DenominationSelector value={denomination} onChange={setDenomination} />
          </div>
          <div style={{flex:1,minHeight:0,overflowY:'auto',padding:'12px'}}>

            {/* SOURCES */}
            {rtab==='sources'&&(
              <div style={{display:'flex',flexDirection:'column',gap:9}}>
                <div style={{fontSize:10,color:'#475569',textTransform:'uppercase',letterSpacing:'.08em',fontWeight:600,padding:'4px 0'}}>
                  {latestSources.length>0?`${latestSources.length} sources retrieved`:'Ask a question to see sources'}
                </div>
                {latestSources.length===0&&(
                  <div style={{padding:'24px 0',textAlign:'center',color:'#334155',fontSize:12}}>
                    Sources will appear here after your first query.
                  </div>
                )}
                {latestSources.map((s,i)=>(
                  <div key={i} className="src-card"
                    style={{padding:'12px',borderRadius:10,background:'rgba(255,255,255,.025)',
                      border:'1px solid rgba(255,255,255,.07)',
                      animation:'fadeUp .3s ease both',animationDelay:`${i*.08}s`}}>
                    <div style={{display:'flex',alignItems:'flex-start',justifyContent:'space-between',marginBottom:6}}>
                      <div style={{flex:1,overflow:'hidden'}}>
                        <div style={{fontSize:12,fontWeight:600,color:'#cbd5e1',marginBottom:2,
                          overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{s.source}</div>
                        <div style={{fontSize:10,color:'#475569',fontFamily:'JetBrains Mono,monospace'}}>
                          Pages: {s.pages?.join(', ')}
                        </div>
                      </div>
                      <div style={{width:22,height:22,borderRadius:5,flexShrink:0,
                        background:'rgba(6,182,212,.1)',border:'1px solid rgba(6,182,212,.2)',
                        display:'flex',alignItems:'center',justifyContent:'center',
                        fontSize:9,color:'#06b6d4',fontWeight:700,fontFamily:'JetBrains Mono,monospace'}}>{i+1}</div>
                    </div>
                    <div style={{marginTop:6,display:'flex',alignItems:'center',gap:4,color:'#334155',fontSize:10}}>
                      <Clock size={9}/>Just now
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* MEMORY */}
            {rtab==='memory'&&(
              <div style={{display:'flex',flexDirection:'column',gap:8}}>
                <div style={{fontSize:10,color:'#475569',textTransform:'uppercase',letterSpacing:'.08em',fontWeight:600,padding:'4px 0'}}>Session context</div>
                {MEMORY.map((m,i)=>(
                  <div key={m.id} style={{padding:'10px 12px',borderRadius:9,
                    background:'rgba(139,92,246,.04)',border:'1px solid rgba(139,92,246,.12)',
                    display:'flex',alignItems:'flex-start',gap:9,
                    animation:'fadeUp .25s ease both',animationDelay:`${i*.07}s`}}>
                    <span style={{fontSize:14,flexShrink:0,marginTop:1}}>{m.icon}</span>
                    <div>
                      <div style={{fontSize:12,color:'#94a3b8',lineHeight:1.45}}>{m.text}</div>
                      <div style={{fontSize:10,color:'#334155',marginTop:3}}>{m.ts}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* DOCS */}
            {rtab==='docs'&&(
              <div style={{display:'flex',flexDirection:'column',gap:9}}>
                <div style={{fontSize:10,color:'#475569',textTransform:'uppercase',letterSpacing:'.08em',fontWeight:600,padding:'4px 0'}}>
                  {docs.length} document{docs.length!==1?'s':''} indexed
                </div>

                {/* Drop zone */}
                <div className={`drop-zone${drag?' drag':''}`}
                  onClick={()=>fileRef.current?.click()}
                  onDragOver={e=>{e.preventDefault();setDrag(true)}}
                  onDragLeave={()=>setDrag(false)}
                  onDrop={e=>{e.preventDefault();setDrag(false);if(e.dataTransfer.files[0])uploadFile(e.dataTransfer.files)}}
                  style={{border:'1.5px dashed rgba(255,255,255,.12)',borderRadius:10,padding:'20px',textAlign:'center'}}>
                  {uploading?(
                    <div style={{display:'flex',flexDirection:'column',alignItems:'center',gap:8}}>
                      <div style={{width:20,height:20,border:'2px solid rgba(6,182,212,.3)',
                        borderTop:'2px solid #06b6d4',borderRadius:'50%',animation:'spin .7s linear infinite'}}/>
                      <div style={{fontSize:11,color:'#06b6d4'}}>Indexing {uploading}…</div>
                      <div style={{width:'100%',height:3,borderRadius:2,background:'rgba(255,255,255,.06)',overflow:'hidden'}}>
                        <div style={{height:'100%',borderRadius:2,background:'#06b6d4',animation:'progress 3s ease forwards'}}/>
                      </div>
                    </div>
                  ):(
                    <>
                      <Upload size={18} color="#475569" style={{marginBottom:6}}/>
                      <div style={{fontSize:11,color:'#64748b'}}>Drop file here</div>
                      <div style={{fontSize:10,color:'#334155',marginTop:2}}>or click to browse</div>
                    </>
                  )}
                </div>

                {/* Doc list */}
                {docs.map((d,i)=>(
                  <div key={d.name} className="doc-row"
                    style={{padding:'10px 12px',borderRadius:9,
                      background:'rgba(255,255,255,.02)',border:'1px solid rgba(255,255,255,.06)',
                      display:'flex',alignItems:'center',gap:8,
                      animation:'fadeUp .3s ease both',animationDelay:`${i*.07}s`}}>
                    <div style={{width:30,height:30,borderRadius:7,flexShrink:0,
                      background:`${d.color}18`,border:`1px solid ${d.color}30`,
                      display:'flex',alignItems:'center',justifyContent:'center'}}>
                      <FileText size={13} color={d.color}/>
                    </div>
                    <div style={{flex:1,overflow:'hidden'}}>
                      <div style={{fontSize:11,fontWeight:600,color:'#cbd5e1',
                        overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{d.name}</div>
                      <div style={{fontSize:10,color:'#475569',fontFamily:'JetBrains Mono,monospace'}}>
                        {d.chunks?`${d.chunks} chunks`:'indexed'} · ready
                      </div>
                    </div>
                    <button className="del-btn icon-btn" onClick={()=>deletePDF(d.name)}
                      style={{width:24,height:24,borderRadius:6,border:'none',cursor:'pointer',
                        background:'transparent',color:'#475569',flexShrink:0,
                        display:'flex',alignItems:'center',justifyContent:'center'}}>
                      <Trash2 size={11}/>
                    </button>
                  </div>
                ))}

                {docs.length===0&&!uploading&&(
                  <div style={{padding:'16px 0',textAlign:'center',color:'#334155',fontSize:12}}>No documents indexed yet.</div>
                )}
              </div>
            )}

            {/* IMAGE */}
            {rtab==='image'&&(
              <div style={{display:'flex',flexDirection:'column',gap:12}}>
                <ImageGenerator token={token} />
              </div>
            )}
          </div>
        </aside>
      )}

      {/* ── COMMAND PALETTE ── */}
      {cmdOpen&&(
        <div onClick={()=>setCmd(false)}
          style={{position:'fixed',inset:0,background:'rgba(0,0,0,.65)',
            backdropFilter:'blur(10px)',zIndex:100,display:'flex',
            alignItems:'flex-start',justifyContent:'center',paddingTop:'14vh'}}>
          <div onClick={e=>e.stopPropagation()}
            style={{width:480,
              background:'rgba(10,12,18,.97)',border:'1px solid rgba(255,255,255,.12)',
              boxShadow:'0 28px 80px rgba(0,0,0,.7),0 0 0 1px rgba(6,182,212,.1)',
              animation:'fadeUp .18s ease',overflow:'hidden'}}>
            <div style={{display:'flex',alignItems:'center',gap:10,padding:'13px 15px',
              borderBottom:'1px solid rgba(255,255,255,.07)'}}>
              <Search size={15} color="#475569"/>
              <input autoFocus placeholder="Search commands, documents, chats…"
                style={{flex:1,background:'none',border:'none',outline:'none',color:'#e2e8f0',fontSize:14,fontFamily:'Inter,sans-serif'}}/>
              <kbd style={{padding:'2px 6px',borderRadius:4,fontSize:10,fontFamily:'JetBrains Mono,monospace',
                background:'rgba(255,255,255,.05)',border:'1px solid rgba(255,255,255,.09)',color:'#475569'}}>ESC</kbd>
            </div>
            <div style={{padding:'5px'}}>
              {CMD.map((item,i)=>(
                <div key={i} className="cmd-item"
                  onClick={()=>{
                    setCmd(false)
                    if(item.key==='U') fileRef.current?.click()
                    if(item.key==='N') setMsgs([])
                    if(item.key==='M'){setRtab('memory');setROpen(true)}
                  }}
                  style={{display:'flex',alignItems:'center',gap:11,padding:'9px 12px',borderRadius:8,transition:'all .1s',cursor:'pointer'}}>
                  <span style={{fontSize:14}}>{item.icon}</span>
                  <span style={{flex:1,fontSize:13,color:'#cbd5e1',fontFamily:'Inter,sans-serif'}}>{item.label}</span>
                  <kbd style={{padding:'2px 7px',borderRadius:4,fontSize:10,fontFamily:'JetBrains Mono,monospace',
                    background:'rgba(255,255,255,.05)',border:'1px solid rgba(255,255,255,.08)',color:'#475569'}}>{item.key}</kbd>
                </div>
              ))}
            </div>
            <div style={{padding:'8px 15px',borderTop:'1px solid rgba(255,255,255,.06)',display:'flex',gap:14}}>
              {[['↑↓','navigate'],['↵','select'],['esc','close']].map(([k,l])=>(
                <div key={k} style={{display:'flex',alignItems:'center',gap:5,fontSize:10,color:'#334155'}}>
                  <kbd style={{padding:'2px 5px',borderRadius:3,fontFamily:'JetBrains Mono,monospace',
                    fontSize:9,background:'rgba(255,255,255,.04)',border:'1px solid rgba(255,255,255,.07)'}}>{k}</kbd>{l}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
