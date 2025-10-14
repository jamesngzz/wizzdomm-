import React, { useEffect, useState } from 'react'

type Exam = {
  id: number
  name: string
  topic: string
  grade_level: string
  created_at: string
  original_image_paths?: string[] | null
}

const API = (import.meta as any).env?.VITE_API_URL || 'http://127.0.0.1:8000/api'
const WS_URL = (import.meta as any).env?.VITE_WS_URL || 'ws://127.0.0.1:8000/ws/notifications/'

import CropperPage from './CropperPage'
import MapperPage from './MapperPage'
import ResultsPage from './ResultsPage'
import SolutionsPage from './SolutionsPage'
import CanvasEditorPage from './CanvasEditorPage'
import SubmissionPage from './SubmissionPage'

export default function App() {
  const [exams, setExams] = useState<Exam[]>([])
  const [status, setStatus] = useState('')
  const [name, setName] = useState('Midterm')
  const [topic, setTopic] = useState('Algebra')
  const [grade, setGrade] = useState('10')
  const [uploadExamId, setUploadExamId] = useState<number | ''>('')
  const [file, setFile] = useState<File | null>(null)

  const loadExams = () => {
    fetch(`${API}/exams/`).then(r => r.json()).then(setExams).catch(e => setStatus(String(e)))
  }

  useEffect(() => {
    loadExams()
    // WebSocket is optional - don't block the app if it fails
    try {
      const ws = new WebSocket(WS_URL)
      ws.onmessage = (e) => setStatus(`WS: ${e.data}`)
      ws.onerror = () => {
        // Silently ignore WebSocket errors - they're not critical
        console.log('WebSocket connection failed (this is normal if WebSocket server is not running)')
      }
      ws.onopen = () => console.log('WebSocket connected')
    } catch (error) {
      console.log('WebSocket not available (this is normal)')
    }
  }, [])

  const createExam = async (e: React.FormEvent) => {
    e.preventDefault()
    setStatus('Creating exam...')
    const res = await fetch(`${API}/exams/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, topic, grade_level: grade })
    })
    if (!res.ok) {
      setStatus(`Create failed: ${res.status}`)
      return
    }
    setStatus('Created')
    setName('')
    loadExams()
  }

  const uploadToExam = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!uploadExamId || !file) { setStatus('Choose exam and file'); return }
    const fd = new FormData()
    fd.append('files', file)
    const res = await fetch(`${API}/exams/${uploadExamId}/upload/`, { method: 'POST', body: fd })
    if (!res.ok) { setStatus(`Upload failed: ${res.status}`); return }
    setStatus('Uploaded')
    loadExams()
  }

  const [view, setView] = useState<'dashboard'|'cropper'|'mapper'|'results'|'solutions'|'canvas'|'submissions'>('dashboard')

  return (
    <div style={{ padding: 20, fontFamily: 'system-ui, -apple-system, Segoe UI, Roboto, Arial' }}>
      <h2>Teacher Assistant</h2>
      <div style={{ marginBottom: 12 }}>Status: {status || '—'}</div>

      <div style={{ marginBottom: 16, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <button onClick={() => setView('dashboard')}>Dashboard</button>
        <button onClick={() => setView('cropper')}>Cropper</button>
        <button onClick={() => setView('submissions')}>Submissions</button>
        <button onClick={() => setView('mapper')}>Mapper</button>
        <button onClick={() => setView('results')}>Results</button>
        <button onClick={() => setView('solutions')}>Solutions</button>
        <button onClick={() => setView('canvas')}>Canvas</button>
        {/* Canvas test/diagnostic removed */}
      </div>

      {view==='dashboard' && <section style={{ marginBottom: 24 }}>
        <h3>Create Exam</h3>
        <form onSubmit={createExam} style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <input placeholder="Name" value={name} onChange={e => setName(e.target.value)} />
          <input placeholder="Topic" value={topic} onChange={e => setTopic(e.target.value)} />
          <input placeholder="Grade" value={grade} onChange={e => setGrade(e.target.value)} />
          <button type="submit">Create</button>
        </form>
      </section>}

      {view==='dashboard' && <section style={{ marginBottom: 24 }}>
        <h3>Upload to Exam</h3>
        <form onSubmit={uploadToExam} style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <select value={uploadExamId} onChange={e => setUploadExamId(Number(e.target.value))}>
            <option value="">Select exam</option>
            {exams.map(ex => (
              <option key={ex.id} value={ex.id}>{ex.name} (#{ex.id})</option>
            ))}
          </select>
          <input type="file" onChange={e => setFile(e.target.files?.[0] || null)} />
          <button type="submit">Upload</button>
        </form>
      </section>}

      {view==='dashboard' && <section>
        <h3>Exams</h3>
        <pre style={{ background: '#f6f6f6', padding: 12 }}>{JSON.stringify(exams, null, 2)}</pre>
      </section>}

      {view==='cropper' && <CropperPage />}
      {view==='submissions' && <SubmissionPage />}
      {view==='mapper' && <MapperPage />}
      {view==='results' && <ResultsPage />}
      {view==='solutions' && <SolutionsPage />}
      {view==='canvas' && <CanvasEditorPage />}
      {/* Canvas test/diagnostic removed */}
    </div>
  )
}


