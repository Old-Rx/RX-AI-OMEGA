import { FormEvent, useCallback, useEffect, useState } from 'react'

type Agent = { id: string; name: string; instructions: string; provider: string | null }
type Step = { id: string; key: string; status: string; risk: string; action: string; output: string | null }
type Mission = { id: string; title: string; objective: string; status: string; steps: Step[]; created_at: string }
type Approval = { id: string; mission_id: string; step_id: string; status: string; reason: string; requested_at: string }
type User = { id: string; username: string; role: string }
type SearchHit = { document_id: string; title: string; score: number; excerpt: string }

const API = import.meta.env.VITE_API_URL ?? ''

async function request<T>(path: string, token?: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    ...init,
    headers: {
      ...(init?.body instanceof URLSearchParams ? { 'Content-Type': 'application/x-www-form-urlencoded' } : { 'Content-Type': 'application/json' }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  })
  if (!response.ok) {
    const data = await response.json().catch(() => ({ detail: 'Request failed' }))
    throw new Error(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail))
  }
  return response.json() as Promise<T>
}

function Status({ value }: { value: string }) {
  return <span className={`status status-${value}`}>{value.replace('_', ' ')}</span>
}

function Login({ onLogin }: { onLogin: (token: string) => void }) {
  const [error, setError] = useState('')
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    try {
      const body = new URLSearchParams({ username: String(form.get('username')), password: String(form.get('password')) })
      const result = await request<{ access_token: string }>('/api/auth/token', undefined, { method: 'POST', body })
      onLogin(result.access_token)
    } catch (err) { setError(err instanceof Error ? err.message : 'Login failed') }
  }
  return <main className="login-shell">
    <section className="login-copy">
      <div className="eyebrow">RX / AUTONOMOUS OPERATIONS</div>
      <h1>Controlled intelligence.<br/><em>Observable action.</em></h1>
      <p>Plan agent work as a dependency graph, hold consequential actions for human review, and preserve the complete operational record.</p>
      <div className="signal"><i></i> Control plane available</div>
    </section>
    <form className="login-card" onSubmit={submit}>
      <div className="mark">Ω</div>
      <h2>Mission Control</h2>
      <p>Authenticate to enter the operations console.</p>
      <label>Username<input name="username" autoComplete="username" required /></label>
      <label>Password<input name="password" type="password" autoComplete="current-password" required /></label>
      {error && <div className="error">{error}</div>}
      <button type="submit">Enter console <span>→</span></button>
    </form>
  </main>
}

export default function App() {
  const [token, setToken] = useState(() => sessionStorage.getItem('rx-token') ?? '')
  const [user, setUser] = useState<User | null>(null)
  const [agents, setAgents] = useState<Agent[]>([])
  const [missions, setMissions] = useState<Mission[]>([])
  const [approvals, setApprovals] = useState<Approval[]>([])
  const [view, setView] = useState<'missions' | 'memory'>('missions')
  const [notice, setNotice] = useState('')
  const logout = useCallback(() => { sessionStorage.removeItem('rx-token'); setToken(''); setUser(null) }, [])

  const refresh = useCallback(async () => {
    if (!token) return
    try {
      const [me, nextAgents, nextMissions, nextApprovals] = await Promise.all([
        request<User>('/api/auth/me', token),
        request<Agent[]>('/api/agents', token),
        request<Mission[]>('/api/missions', token),
        request<Approval[]>('/api/approvals', token),
      ])
      setUser(me); setAgents(nextAgents); setMissions(nextMissions); setApprovals(nextApprovals)
    } catch (err) {
      if (err instanceof Error && err.message.includes('credentials')) logout()
      else setNotice(err instanceof Error ? err.message : 'Unable to refresh')
    }
  }, [token, logout])

  useEffect(() => { void refresh() }, [refresh])

  const login = (value: string) => { sessionStorage.setItem('rx-token', value); setToken(value) }
  if (!token) return <Login onLogin={login} />

  const createAgent = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); const form = new FormData(event.currentTarget)
    try {
      await request('/api/agents', token, { method: 'POST', body: JSON.stringify({ name: form.get('name'), instructions: form.get('instructions'), provider: form.get('provider') || null }) })
      event.currentTarget.reset(); setNotice('Agent registered'); await refresh()
    } catch (err) { setNotice(err instanceof Error ? err.message : 'Could not create agent') }
  }
  const createMission = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); const form = new FormData(event.currentTarget)
    try {
      await request('/api/missions', token, { method: 'POST', body: JSON.stringify({
        title: form.get('title'), objective: form.get('objective'),
        steps: [{ key: 'execute', agent_id: form.get('agent_id'), prompt: form.get('prompt'), depends_on: [], risk: form.get('risk'), action: form.get('action') }],
      }) })
      event.currentTarget.reset(); setNotice('Mission drafted'); await refresh()
    } catch (err) { setNotice(err instanceof Error ? err.message : 'Could not create mission') }
  }
  const act = async (path: string, message: string) => {
    try { await request(path, token, { method: 'POST', body: JSON.stringify({ note: 'Decision recorded in operations console' }) }); setNotice(message); await refresh() }
    catch (err) { setNotice(err instanceof Error ? err.message : 'Action failed') }
  }

  const pending = approvals.filter(item => item.status === 'pending')
  const complete = missions.filter(item => item.status === 'completed').length
  return <div className="app-shell">
    <aside>
      <div className="brand"><span>Ω</span><div><b>RX-AI</b><small>OMEGA</small></div></div>
      <nav>
        <button className={view === 'missions' ? 'active' : ''} onClick={() => setView('missions')}>◈ Operations</button>
        <button className={view === 'memory' ? 'active' : ''} onClick={() => setView('memory')}>◇ Memory</button>
      </nav>
      <div className="identity"><div>{user?.username.slice(0, 2).toUpperCase()}</div><span><b>{user?.username}</b><small>{user?.role}</small></span><button onClick={logout}>↗</button></div>
    </aside>
    <main className="workspace">
      <header><div><div className="eyebrow">OPERATIONS / LIVE</div><h1>{view === 'missions' ? 'Mission control' : 'Knowledge memory'}</h1></div><button className="refresh" onClick={() => void refresh()}>↻ Refresh</button></header>
      {notice && <div className="notice" onClick={() => setNotice('')}>{notice}<span>×</span></div>}
      {view === 'missions' ? <>
        <section className="stats">
          <article><small>Total missions</small><strong>{missions.length}</strong><span>Persisted records</span></article>
          <article><small>Completed</small><strong>{complete}</strong><span>Verified terminal state</span></article>
          <article className={pending.length ? 'attention' : ''}><small>Awaiting approval</small><strong>{pending.length}</strong><span>Human decision required</span></article>
          <article><small>Registered agents</small><strong>{agents.length}</strong><span>Available executors</span></article>
        </section>
        {pending.length > 0 && <section className="panel approvals"><div className="panel-heading"><div><span className="eyebrow">HUMAN CONTROL</span><h2>Approval queue</h2></div></div>
          {pending.map(item => <div className="approval-row" key={item.id}><div><Status value="waiting_approval"/><b>{item.reason}</b><small>Mission {item.mission_id.slice(0, 8)} · Step {item.step_id.slice(0, 8)}</small></div>{user?.role === 'admin' && <div><button className="ghost danger" onClick={() => void act(`/api/approvals/${item.id}/reject`, 'Action rejected')}>Reject</button><button onClick={() => void act(`/api/approvals/${item.id}/approve`, 'Action approved and resumed')}>Approve & resume</button></div>}</div>)}
        </section>}
        <div className="grid">
          <section className="panel span-2"><div className="panel-heading"><div><span className="eyebrow">EXECUTION LEDGER</span><h2>Recent missions</h2></div></div>
            <div className="mission-list">{missions.length === 0 && <div className="empty">No missions yet. Draft the first controlled workflow.</div>}{missions.map(mission => <article key={mission.id}><div className="mission-main"><Status value={mission.status}/><h3>{mission.title}</h3><p>{mission.objective}</p><small>{new Date(mission.created_at).toLocaleString()}</small></div><div className="step-list">{mission.steps.map(step => <div key={step.id}><span>{step.key}</span><Status value={step.status}/>{step.output && <p>{step.output}</p>}</div>)}</div>{mission.status === 'draft' && user?.role !== 'viewer' && <button onClick={() => void act(`/api/missions/${mission.id}/run`, 'Mission queued')}>Run mission →</button>}</article>)}</div>
          </section>
          <div className="stack">
            {user?.role !== 'viewer' && <section className="panel compact"><div className="panel-heading"><div><span className="eyebrow">NEW WORKFLOW</span><h2>Draft mission</h2></div></div>
              {agents.length ? <form onSubmit={createMission}><label>Title<input name="title" required/></label><label>Objective<textarea name="objective" required/></label><label>Execution prompt<textarea name="prompt" required/></label><label>Agent<select name="agent_id">{agents.map(a => <option value={a.id} key={a.id}>{a.name}</option>)}</select></label><div className="form-row"><label>Risk<select name="risk"><option>low</option><option>medium</option><option>high</option></select></label><label>Action<select name="action"><option>analysis</option><option>production</option><option>release</option><option>deploy</option></select></label></div><button type="submit">Create draft</button></form> : <div className="empty">Register an agent first.</div>}
            </section>}
            {user?.role !== 'viewer' && <section className="panel compact"><div className="panel-heading"><div><span className="eyebrow">CAPABILITY</span><h2>Register agent</h2></div></div><form onSubmit={createAgent}><label>Name<input name="name" required/></label><label>Instructions<textarea name="instructions" required/></label><label>Provider<select name="provider"><option value="">Platform default</option><option>mock</option><option>openai</option><option>ollama</option></select></label><button type="submit">Register</button></form></section>}
          </div>
        </div>
      </> : <Memory token={token} canWrite={user?.role !== 'viewer'} />}
    </main>
  </div>
}

function Memory({ token, canWrite }: { token: string; canWrite: boolean }) {
  const [hits, setHits] = useState<SearchHit[]>([]); const [message, setMessage] = useState('')
  const ingest = async (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); const form = new FormData(event.currentTarget); try { await request('/api/documents', token, { method: 'POST', body: JSON.stringify({ title: form.get('title'), content: form.get('content'), metadata: { source: 'console' } }) }); event.currentTarget.reset(); setMessage('Document indexed') } catch (err) { setMessage(err instanceof Error ? err.message : 'Ingestion failed') } }
  const search = async (event: FormEvent<HTMLFormElement>) => { event.preventDefault(); const form = new FormData(event.currentTarget); try { setHits(await request<SearchHit[]>(`/api/documents/search?q=${encodeURIComponent(String(form.get('q')))}`, token)) } catch (err) { setMessage(err instanceof Error ? err.message : 'Search failed') } }
  return <div className="grid memory-grid"><section className="panel"><div className="panel-heading"><div><span className="eyebrow">RETRIEVAL</span><h2>Search memory</h2></div></div><form onSubmit={search}><label>Query<input name="q" required placeholder="What should the agents know?"/></label><button>Search</button></form><div className="hits">{hits.map(hit => <article key={hit.document_id}><b>{hit.title}</b><small>Relevance {(hit.score * 100).toFixed(1)}%</small><p>{hit.excerpt}</p></article>)}</div></section>{canWrite && <section className="panel"><div className="panel-heading"><div><span className="eyebrow">INGESTION</span><h2>Add source</h2></div></div><form onSubmit={ingest}><label>Title<input name="title" required/></label><label>Content<textarea name="content" rows={12} required/></label><button>Index document</button>{message && <p className="form-message">{message}</p>}</form></section>}</div>
}
