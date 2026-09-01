import {useEffect,useMemo,useState} from 'react';
import {Send,Copy,Search,Plus,MessageSquare,Clock3} from 'lucide-react';
import api from '../../api/client';
import GlassCard from '../../components/GlassCard/GlassCard';
import CitationCard from '../../components/CitationCard/CitationCard';
import ConfidenceGauge from '../../components/ConfidenceGauge/ConfidenceGauge';
import SafetyAlert from '../../components/SafetyAlert/SafetyAlert';
import './Chat.css';

const examples=['What does error code E05 mean?','Why is the hydraulic pressure low?','When should I perform an emergency shutdown?'];

export default function Chat(){
  const [manuals,setManuals]=useState([]);
  const [manualId,setManualId]=useState('');
  const [question,setQuestion]=useState('');
  const [manualSearch,setManualSearch]=useState('');
  const [evidenceSearch,setEvidenceSearch]=useState('');
  const [answer,setAnswer]=useState(null);
  const [busy,setBusy]=useState(false);
  const [conversationId,setConversationId]=useState(null);
  const [conversations,setConversations]=useState([]);
  const [historyOpen,setHistoryOpen]=useState(true);

  const loadConversations=async()=>{
    try{
      const r=await api.get('/conversations');
      setConversations(r.data||[]);
    }catch(e){
      setConversations([]);
    }
  };

  useEffect(()=>{
    api.get('/manuals').then(r=>{
      const indexed=r.data.filter(x=>x.status==='indexed');
      setManuals(indexed);
      if(indexed[0]) setManualId(indexed[0].id);
    }).catch(()=>{});
    loadConversations();
  },[]);

  const filteredManuals=useMemo(()=>{
    const q=manualSearch.trim().toLowerCase();
    if(!q) return manuals;
    return manuals.filter(m=>[m.filename,m.equipment_name,m.manufacturer,m.model_number,m.version].join(' ').toLowerCase().includes(q));
  },[manuals,manualSearch]);

  const filteredCitations=useMemo(()=>{
    const q=evidenceSearch.trim().toLowerCase();
    if(!q) return answer?.citations||[];
    return (answer?.citations||[]).filter(c=>[c.manual_name,c.section_title,c.excerpt,String(c.page_number)].join(' ').toLowerCase().includes(q));
  },[answer,evidenceSearch]);

  const newChat=()=>{
    setConversationId(null);
    setQuestion('');
    setAnswer(null);
    setEvidenceSearch('');
    setBusy(false);
  };

  const openConversation=async(id)=>{
    try{
      const r=await api.get(`/conversations/${id}`);
      setConversationId(id);
      setQuestion('');
      setAnswer(null);
      setEvidenceSearch('');
      const messages=r.data?.messages||[];
      const lastAssistant=[...messages].reverse().find(m=>m.role==='assistant');
      const lastUser=[...messages].reverse().find(m=>m.role==='user');
      if(lastAssistant){
        setAnswer({
          answer:lastAssistant.content,
          troubleshooting_steps:[],
          safety_warnings:[],
          citations:[],
          confidence:{score:lastAssistant.confidence_score||0},
        });
      }
      if(lastUser) setQuestion(lastUser.content);
    }catch(e){}
  };

  const ask=async q=>{
    q=q||question;
    if(!q.trim()||busy) return;
    setQuestion(q); setBusy(true); setAnswer(null); setEvidenceSearch('');
    try{
      const r=await api.post('/chat/query',{
        question:q,
        manual_ids:manualId?[manualId]:[],
        conversation_id:conversationId,
        top_k:6
      });
      setAnswer(r.data);
      setConversationId(r.data.conversation_id);
      await loadConversations();
    }catch(e){
      setAnswer({answer:e.response?.data?.detail||'Unable to complete the troubleshooting request.',troubleshooting_steps:[],safety_warnings:[],citations:[],confidence:{score:0}});
    }finally{setBusy(false)}
  };

  return <div className="chat-page">
    <main className="chat-main">
      <header className="chat-header">
        <div className="chat-title">
          <h1>Troubleshooting Assistant</h1>
          <p>Search your manuals, ask a question, and review the evidence supporting the response.</p>
        </div>
        <button className="btn btn-primary new-chat-btn" onClick={newChat}><Plus size={18}/> New chat</button>
      </header>

      <section className="chat-toolbar" aria-label="Chat tools">
        <div className="chat-search-bar">
          <label className="search-field"><Search size={17}/><span>Manual</span><input value={manualSearch} onChange={e=>setManualSearch(e.target.value)} placeholder="Search manual, equipment, model…"/></label>
          <label className="search-field"><Search size={17}/><span>Evidence</span><input value={evidenceSearch} onChange={e=>setEvidenceSearch(e.target.value)} placeholder="Search retrieved evidence…"/></label>
          <select aria-label="Selected manual" value={manualId} onChange={e=>setManualId(e.target.value)}>
            <option value="">All indexed manuals</option>
            {filteredManuals.map(m=><option key={m.id} value={m.id}>{m.filename} · {m.model_number}</option>)}
          </select>
        </div>
      </section>

      <section className="conversation-history" aria-label="Previous chats">
        <button className="history-toggle" onClick={()=>setHistoryOpen(v=>!v)}><Clock3 size={16}/><span>Previous chats</span><b>{conversations.length}</b></button>
        {historyOpen&&<div className="history-list">
          {conversations.length===0&&<span className="history-empty">Previous chats will appear here after your first question.</span>}
          {conversations.slice(0,8).map(c=><button className={`history-item ${conversationId===c.id?'active':''}`} key={c.id} onClick={()=>openConversation(c.id)}><MessageSquare size={16}/><span>{c.title}</span></button>)}
        </div>}
      </section>

      {!answer&&!busy&&<section className="welcome"><div className="welcome-core">EA</div><h2>What equipment issue can I help diagnose?</h2><p>Choose a verified manual, then describe the exact error code, model, or symptom.</p><div>{examples.map(q=><button className="btn" key={q} onClick={()=>ask(q)}>{q}</button>)}</div></section>}
      {busy&&<div className="retrieving"><i/><span>Analyzing query, retrieving evidence, and validating citations…</span></div>}
      {answer&&<div className="answer"><GlassCard><div className="answer-head"><h2>Evidence-grounded response</h2><button className="btn" onClick={()=>navigator.clipboard?.writeText(answer.answer)}><Copy size={16}/> Copy</button></div><SafetyAlert warnings={answer.safety_warnings||[]}/><div className="answer-copy">{answer.answer}</div>{(answer.troubleshooting_steps||[]).length>0&&<><h3>Troubleshooting steps</h3><ol>{answer.troubleshooting_steps.map((x,i)=><li key={i}><span>{i+1}</span><div>{x}<small>Verify the documented condition before continuing.</small></div></li>)}</ol></>}<ConfidenceGauge confidence={answer.confidence||{score:0}}/></GlassCard></div>}

      <div className="composer"><div><label htmlFor="question">Equipment question</label><textarea id="question" value={question} onChange={e=>setQuestion(e.target.value)} placeholder="Enter an exact error code, symptom, and equipment model…" onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();ask()}}}/><button aria-label="Send question" onClick={()=>ask()} disabled={busy}><Send/></button></div><small>EquipAssist uses retrieved manual evidence and refuses unsupported repair instructions.</small></div>
    </main>

    <section className="evidence-section" aria-label="Evidence">
      <div className="evidence-header"><div><h2>Evidence</h2><p className="muted">Supporting manual passages for the current response.</p></div><span className="evidence-count">{filteredCitations.length} matching source passage{filteredCitations.length===1?'':'s'}</span></div>
      <div className="evidence-grid">
        {filteredCitations.map((c,i)=><CitationCard citation={c} index={i} key={c.chunk_id}/>) }
        {!answer&&<p className="empty-evidence">Citations will appear here after a question.</p>}
        {answer&&filteredCitations.length===0&&<p className="empty-evidence">No evidence matches the current evidence search.</p>}
      </div>
    </section>
  </div>
}
