import React, { useEffect, useState } from 'react'
import Cropper from 'react-easy-crop'

const API = (import.meta as any).env?.VITE_API_URL || 'http://127.0.0.1:8000/api'

type QuestionRef = { id: number, label: string }

export default function MapperPage() {
  const [submissionId, setSubmissionId] = useState<number | ''>('')
  const [examId, setExamId] = useState<number | ''>('')
  const [questions, setQuestions] = useState<QuestionRef[]>([])
  const [questionId, setQuestionId] = useState<number | ''>('')
  const [images, setImages] = useState<string[]>([])
  const [page, setPage] = useState(0)
  const [crop, setCrop] = useState({ x: 0, y: 0 })
  const [zoom, setZoom] = useState(1)
  const [croppedAreaPixels, setCroppedAreaPixels] = useState<any>(null)
  const [status, setStatus] = useState('')

  useEffect(() => {
    if (!examId) { setQuestions([]); return }
    fetch(`${API}/exams/${examId}/questions/`).then(r => r.json()).then(d => setQuestions(d.items || [])).catch(e => setStatus(String(e)))
  }, [examId])

  useEffect(() => {
    if (!submissionId) { setImages([]); return }
    fetch(`${API}/submissions/${submissionId}/images/`).then(r => r.json()).then(d => setImages(d.urls || [])).catch(e => setStatus(String(e)))
  }, [submissionId])

  const onCropComplete = (_a: any, pixels: any) => setCroppedAreaPixels(pixels)

  const saveMapping = async () => {
    if (!submissionId || !questionId || !croppedAreaPixels) { setStatus('Missing data'); return }
    const bbox = { left: Math.max(0, Math.round(croppedAreaPixels.x)), top: Math.max(0, Math.round(croppedAreaPixels.y)), width: Math.round(croppedAreaPixels.width), height: Math.round(croppedAreaPixels.height) }
    const res = await fetch(`${API}/submissions/${submissionId}/items/`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question_id: questionId, page_index: page, bbox }) })
    if (!res.ok) { setStatus(`Save failed: ${res.status}`); return }
    setStatus('Mapped answer saved')
  }

  const gradeSubmission = async () => {
    if (!submissionId) return
    const res = await fetch(`${API}/submissions/${submissionId}/grade/`, { method: 'POST' })
    if (!res.ok) { setStatus(`Grade failed: ${res.status}`); return }
    setStatus('Grading triggered')
  }

  return (
    <div style={{ padding: 20 }}>
      <h3>Answer Mapper</h3>
      <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
        <input placeholder="Submission ID" value={submissionId} onChange={e => setSubmissionId(Number(e.target.value))} style={{ width: 130 }} />
        <input placeholder="Exam ID" value={examId} onChange={e => setExamId(Number(e.target.value))} style={{ width: 100 }} />
        <select value={questionId} onChange={e => setQuestionId(Number(e.target.value))}>
          <option value="">Select question</option>
          {questions.map(q => <option key={q.id} value={q.id}>{q.label}</option>)}
        </select>
        <button onClick={saveMapping}>Save Mapping</button>
        <button onClick={gradeSubmission}>Grade Submission</button>
        <span>{status}</span>
      </div>
      {images.length > 0 && (
        <div>
          <div style={{ marginBottom: 8 }}>
            <button disabled={page === 0} onClick={() => setPage(p => Math.max(0, p - 1))}>Prev</button>
            <span style={{ margin: '0 8px' }}>Page {page + 1} / {images.length}</span>
            <button disabled={page === images.length - 1} onClick={() => setPage(p => Math.min(images.length - 1, p + 1))}>Next</button>
          </div>
          <div style={{ position: 'relative', width: 600, height: 800, background: '#eee' }}>
            <Cropper
              image={images[page]}
              crop={crop}
              zoom={zoom}
              aspect={4/3}
              onCropChange={setCrop}
              onZoomChange={setZoom}
              onCropComplete={onCropComplete}
            />
          </div>
        </div>
      )}
    </div>
  )
}



