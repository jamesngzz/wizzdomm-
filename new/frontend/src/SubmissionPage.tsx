import React, { useEffect, useState } from 'react'
import DragCropSelector from './DragCropSelector'

const API = (import.meta as any).env?.VITE_API_URL || 'http://127.0.0.1:8000/api'

type Submission = {
  id: number
  exam: number
  student_name: string
  original_image_paths: string[] | null
  created_at: string
}

type SubmissionImageList = { count: number, urls: string[] }

type Question = {
  id: number
  label: string
}

export default function SubmissionPage() {
  const [submissions, setSubmissions] = useState<Submission[]>([])
  const [selectedSubmissionId, setSelectedSubmissionId] = useState<number | ''>('')
  const [images, setImages] = useState<string[]>([])
  const [page, setPage] = useState(0)
  const [cropArea, setCropArea] = useState<{ x: number; y: number; width: number; height: number } | null>(null)
  const [selectedQuestionId, setSelectedQuestionId] = useState<number | ''>('')
  const [questions, setQuestions] = useState<Question[]>([])
  const [status, setStatus] = useState('')
  const [newSubmissionData, setNewSubmissionData] = useState({
    exam: '',
    student_name: ''
  })
  const [file, setFile] = useState<File | null>(null)

  // Load submissions
  useEffect(() => {
    fetch(`${API}/submissions/`)
      .then(r => r.json())
      .then(setSubmissions)
      .catch(e => setStatus(`Error loading submissions: ${e}`))
  }, [])

  // Load questions when exam changes
  useEffect(() => {
    if (newSubmissionData.exam) {
      fetch(`${API}/exams/${newSubmissionData.exam}/questions/`)
        .then(r => r.json())
        .then((data: { count: number, items: Question[] }) => setQuestions(data.items || []))
        .catch(() => setQuestions([]))
    } else {
      setQuestions([])
    }
  }, [newSubmissionData.exam])

  // Load submission images and questions when submission changes
  useEffect(() => {
    if (!selectedSubmissionId) { 
      setImages([])
      setQuestions([])
      return 
    }
    
    // Find the selected submission to get its exam ID
    const selectedSubmission = submissions.find(sub => sub.id === selectedSubmissionId)
    if (!selectedSubmission) return
    
    // Load questions from the submission's exam
    if (selectedSubmission.exam) {
      setStatus('Loading questions and images...')
      fetch(`${API}/exams/${selectedSubmission.exam}/questions/`)
        .then(r => r.json())
        .then((data: { count: number, items: Question[] }) => {
          setQuestions(data.items || [])
          console.log('Loaded questions for exam', selectedSubmission.exam, ':', data.items)
        })
        .catch(e => {
          console.error('Error loading questions:', e)
          setQuestions([])
        })
    }
    
    // Load submission images
    setStatus('Loading submission images...')
    fetch(`${API}/submissions/${selectedSubmissionId}/images/`)
      .then(r => r.json())
      .then((d: SubmissionImageList) => {
        console.log('Submission images API response:', d)
        const urls = d.urls || []
        // Convert relative URLs to absolute URLs
        const absoluteUrls = urls.map(url => 
          url.startsWith('http') ? url : `${API.replace('/api', '')}${url}`
        )
        console.log('Original URLs:', urls)
        console.log('Absolute URLs:', absoluteUrls)
        setImages(absoluteUrls)
        setStatus(`Loaded ${absoluteUrls.length} submission images`)
      })
      .catch(e => {
        console.error('Error loading submission images:', e)
        setStatus(String(e))
      })
  }, [selectedSubmissionId, submissions])

  const createSubmission = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newSubmissionData.exam || !newSubmissionData.student_name) {
      setStatus('Please fill in exam ID and student name')
      return
    }

    setStatus('Creating submission...')
    const res = await fetch(`${API}/submissions/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        exam: Number(newSubmissionData.exam),
        student_name: newSubmissionData.student_name
      })
    })

    if (!res.ok) {
      setStatus(`Create failed: ${res.status}`)
      return
    }

    const newSubmission = await res.json()
    setSubmissions(prev => [newSubmission, ...prev])
    setStatus('Submission created successfully!')
    setNewSubmissionData({ exam: '', student_name: '' })
  }

  const uploadToSubmission = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedSubmissionId || !file) { 
      setStatus('Choose submission and file')
      return 
    }

    const fd = new FormData()
    fd.append('files', file)
    
    setStatus('Uploading file...')
    const res = await fetch(`${API}/submissions/${selectedSubmissionId}/upload/`, { 
      method: 'POST', 
      body: fd 
    })
    
    if (!res.ok) { 
      setStatus(`Upload failed: ${res.status}`)
      return 
    }
    
    setStatus('File uploaded successfully!')
    setFile(null)
    
    // Refresh submission images
    fetch(`${API}/submissions/${selectedSubmissionId}/images/`)
      .then(r => r.json())
      .then((d: SubmissionImageList) => {
        const urls = d.urls || []
        const absoluteUrls = urls.map(url => 
          url.startsWith('http') ? url : `${API.replace('/api', '')}${url}`
        )
        setImages(absoluteUrls)
      })
      .catch(console.error)
  }

  const handleCropComplete = (bbox: { x: number; y: number; width: number; height: number }) => {
    setCropArea(bbox)
    setStatus(`Selection: ${bbox.width}x${bbox.height} at (${bbox.x}, ${bbox.y})`)
  }

  const handleCropChange = (bbox: { x: number; y: number; width: number; height: number }) => {
    setCropArea(bbox)
  }

  const submitCrop = async () => {
    if (!selectedSubmissionId || !images[page] || !cropArea || !selectedQuestionId) { 
      setStatus('Please select submission, image, area, and question')
      return 
    }
    
    const bbox = {
      left: Math.max(0, cropArea.x),
      top: Math.max(0, cropArea.y),
      width: Math.max(10, cropArea.width),
      height: Math.max(10, cropArea.height)
    }
    
    setStatus('Saving submission item...')
    const res = await fetch(`${API}/submissions/${selectedSubmissionId}/items/`, { 
      method: 'POST', 
      headers: { 'Content-Type': 'application/json' }, 
      body: JSON.stringify({ 
        question_id: selectedQuestionId, 
        page_index: page, 
        bbox 
      }) 
    })
    
    if (!res.ok) { 
      setStatus(`Save failed: ${res.status}`)
      return 
    }
    
    setStatus('Submission item saved successfully!')
    setCropArea(null)
  }

  return (
    <div style={{ padding: 20 }}>
      <h3>Submission Management</h3>
      
      {/* Create New Submission */}
      <section style={{ marginBottom: 24, border: '1px solid #ddd', padding: 16, borderRadius: 8 }}>
        <h4>Create New Submission</h4>
        <form onSubmit={createSubmission} style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          <input 
            placeholder="Exam ID" 
            value={newSubmissionData.exam} 
            onChange={e => setNewSubmissionData(prev => ({ ...prev, exam: e.target.value }))} 
            style={{ width: 100 }} 
          />
          <input 
            placeholder="Student Name" 
            value={newSubmissionData.student_name} 
            onChange={e => setNewSubmissionData(prev => ({ ...prev, student_name: e.target.value }))} 
            style={{ width: 150 }} 
          />
          <button type="submit">Create Submission</button>
        </form>
      </section>

      {/* Upload to Existing Submission */}
      <section style={{ marginBottom: 24, border: '1px solid #ddd', padding: 16, borderRadius: 8 }}>
        <h4>Upload to Submission</h4>
        <form onSubmit={uploadToSubmission} style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          <select value={selectedSubmissionId} onChange={e => setSelectedSubmissionId(Number(e.target.value))}>
            <option value="">Select submission</option>
            {submissions.map(sub => (
              <option key={sub.id} value={sub.id}>
                {sub.student_name} - Exam {sub.exam} (#{sub.id})
              </option>
            ))}
          </select>
          <input 
            type="file" 
            onChange={e => setFile(e.target.files?.[0] || null)} 
            accept="image/*,.pdf"
          />
          <button type="submit" disabled={!selectedSubmissionId || !file}>Upload</button>
        </form>
      </section>

      {/* Crop Submission to Questions */}
      {images.length > 0 && (
        <section style={{ marginBottom: 24, border: '1px solid #ddd', padding: 16, borderRadius: 8 }}>
          <h4>Crop Submission to Questions</h4>
          {selectedSubmissionId && (() => {
            const selectedSubmission = submissions.find(sub => sub.id === selectedSubmissionId)
            return selectedSubmission ? (
              <div style={{ marginBottom: 12, fontSize: '12px', color: '#666' }}>
                Submission: {selectedSubmission.student_name} | Exam: {selectedSubmission.exam} | 
                Questions loaded: {questions.length}
              </div>
            ) : null
          })()}
          
          <div style={{ display: 'flex', gap: 12, marginBottom: 12, alignItems: 'center', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <label style={{ fontSize: '14px', fontWeight: 'bold' }}>Match to Question:</label>
              <select value={selectedQuestionId} onChange={e => setSelectedQuestionId(Number(e.target.value))}>
                <option value="">Select question to match</option>
                {questions.map(q => (
                  <option key={q.id} value={q.id}>{q.label}</option>
                ))}
              </select>
            </div>
            {questions.length === 0 && selectedSubmissionId && (
              <span style={{ fontSize: '12px', color: '#666' }}>
                No questions found for this exam. Make sure the exam has questions created in the Cropper page.
              </span>
            )}
            <button onClick={submitCrop} disabled={!cropArea || !selectedQuestionId}>
              Save Submission Item
            </button>
            <button onClick={() => setCropArea(null)} disabled={!cropArea}>
              Clear Selection
            </button>
            <span>{status}</span>
          </div>

          <div style={{ marginBottom: 8 }}>
            <button disabled={page === 0} onClick={() => setPage(p => Math.max(0, p - 1))}>Prev</button>
            <span style={{ margin: '0 8px' }}>Page {page + 1} / {images.length}</span>
            <button disabled={page === images.length - 1} onClick={() => setPage(p => Math.min(images.length - 1, p + 1))}>Next</button>
          </div>

          <div style={{ marginBottom: 8, fontSize: '12px', color: '#666' }}>
            Current image URL: {images[page]}
          </div>

          <div style={{ border: '2px solid #ddd', borderRadius: '8px', padding: '16px', backgroundColor: '#f9f9f9' }}>
            <div style={{ marginBottom: '12px', fontSize: '14px', fontWeight: 'bold' }}>
              Drag to Select Answer Area
            </div>
            <DragCropSelector
              imageUrl={images[page]}
              onCropComplete={handleCropComplete}
              onCropChange={handleCropChange}
            />
          </div>
        </section>
      )}

      {/* Submissions List */}
      <section>
        <h4>All Submissions</h4>
        <pre style={{ background: '#f6f6f6', padding: 12, maxHeight: 300, overflow: 'auto' }}>
          {JSON.stringify(submissions, null, 2)}
        </pre>
      </section>
    </div>
  )
}
