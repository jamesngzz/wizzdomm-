import React, { useState } from 'react'

const API = (import.meta as any).env?.VITE_API_URL || 'http://127.0.0.1:8000/api'

export default function SolutionsPage() {
  const [questionId, setQuestionId] = useState<number | ''>('')
  const [data, setData] = useState<any>(null)
  const [status, setStatus] = useState('')
  const [ver, setVer] = useState(false)

  const load = async () => {
    if (!questionId) return
    setStatus('Loading...')
    const res = await fetch(`${API}/questions/${questionId}/solution/`)
    if (!res.ok) { setStatus(`Failed: ${res.status}`); return }
    const d = await res.json()
    setData(d)
    setVer(!!d.verified)
    setStatus('')
  }

  const solve = async () => {
    if (!questionId) return
    setStatus('Solving...')
    const res = await fetch(`${API}/questions/${questionId}/solve/`, { method: 'POST' })
    if (!res.ok) { setStatus(`Solve failed: ${res.status}`); return }
    await load()
    setStatus('Solved')
  }

  const verify = async () => {
    if (!questionId) return
    setStatus('Updating...')
    const res = await fetch(`${API}/questions/${questionId}/verify/`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ verified: ver }) })
    if (!res.ok) { setStatus(`Verify failed: ${res.status}`); return }
    await load()
    setStatus('Updated')
  }

  return (
    <div style={{ padding: 20 }}>
      <h3>Solutions</h3>
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <input placeholder="Question ID" value={questionId} onChange={e => setQuestionId(Number(e.target.value))} style={{ width: 130 }} />
        <button onClick={load}>Load</button>
        <button onClick={solve}>Solve</button>
        <label style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
          <input type="checkbox" checked={ver} onChange={e => setVer(e.target.checked)} /> Verified
        </label>
        <button onClick={verify}>Save</button>
        <span>{status}</span>
      </div>
      {data && (
        <pre style={{ background: '#f6f6f6', padding: 12 }}>{JSON.stringify(data, null, 2)}</pre>
      )}
    </div>
  )
}



