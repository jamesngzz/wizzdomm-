import React, { useEffect, useState } from 'react'
import DragCropSelector from './DragCropSelector'

const API = (import.meta as any).env?.VITE_API_URL || 'http://127.0.0.1:8000/api'

type ExamImageList = { count: number, urls: string[] }

export default function CropperPage() {
  const [examId, setExamId] = useState<number | ''>('')
  const [images, setImages] = useState<string[]>([])
  const [page, setPage] = useState(0)
  const [cropArea, setCropArea] = useState<{ x: number; y: number; width: number; height: number } | null>(null)
  const [label, setLabel] = useState('1a')
  const [status, setStatus] = useState('')

  useEffect(() => {
    if (!examId) { setImages([]); return }
    setStatus('Loading images...')
    fetch(`${API}/exams/${examId}/images/`)
      .then(r => r.json())
      .then((d: ExamImageList) => {
        console.log('Images API response:', d)
        const urls = d.urls || []
        // Convert relative URLs to absolute URLs
        const absoluteUrls = urls.map(url => 
          url.startsWith('http') ? url : `${API.replace('/api', '')}${url}`
        )
        console.log('Original URLs:', urls)
        console.log('Absolute URLs:', absoluteUrls)
        setImages(absoluteUrls)
        setStatus(`Loaded ${absoluteUrls.length} images`)
      })
      .catch(e => {
        console.error('Error loading images:', e)
        setStatus(String(e))
      })
  }, [examId])

  const handleCropComplete = (bbox: { x: number; y: number; width: number; height: number }) => {
    setCropArea(bbox)
    setStatus(`Selection: ${bbox.width}x${bbox.height} at (${bbox.x}, ${bbox.y})`)
  }

  const handleCropChange = (bbox: { x: number; y: number; width: number; height: number }) => {
    setCropArea(bbox)
  }

  const submitCrop = async () => {
    if (!examId || !images[page] || !cropArea) { setStatus('Please select an area first'); return }
    
    // Convert coordinates to the format expected by the backend
    const bbox = {
      left: Math.max(0, cropArea.x),
      top: Math.max(0, cropArea.y),
      width: Math.max(10, cropArea.width), // Minimum width
      height: Math.max(10, cropArea.height) // Minimum height
    }
    
    setStatus('Saving crop...')
    const res = await fetch(`${API}/questions/`, { 
      method: 'POST', 
      headers: { 'Content-Type': 'application/json' }, 
      body: JSON.stringify({ exam: examId, label, page_index: page, bbox }) 
    })
    
    if (!res.ok) { 
      setStatus(`Crop failed: ${res.status}`); 
      return 
    }
    
    setStatus('Question saved successfully!')
    setCropArea(null) // Clear selection after saving
  }

  return (
    <div style={{ padding: 20 }}>
      <h3>Crop Question</h3>
      <div style={{ display: 'flex', gap: 12, marginBottom: 12, alignItems: 'center' }}>
        <input placeholder="Exam ID" value={examId} onChange={e => setExamId(Number(e.target.value))} style={{ width: 100 }} />
        <input placeholder="Label (e.g., 1a)" value={label} onChange={e => setLabel(e.target.value)} style={{ width: 120 }} />
        <button onClick={submitCrop} disabled={!cropArea}>Save Crop</button>
        <button onClick={() => setCropArea(null)} disabled={!cropArea}>Clear Selection</button>
        <span>{status}</span>
      </div>
      {images.length > 0 && (
        <div>
          <div style={{ marginBottom: 8 }}>
            <button disabled={page === 0} onClick={() => setPage(p => Math.max(0, p - 1))}>Prev</button>
            <span style={{ margin: '0 8px' }}>Page {page + 1} / {images.length}</span>
            <button disabled={page === images.length - 1} onClick={() => setPage(p => Math.min(images.length - 1, p + 1))}>Next</button>
          </div>
          <div style={{ marginBottom: 8, fontSize: '12px', color: '#666' }}>
            Current image URL: {images[page]}
          </div>
          <div style={{ marginBottom: 8, border: '1px solid #ccc', padding: 8 }}>
            <div style={{ fontSize: '12px', marginBottom: 4 }}>Direct image test:</div>
            <img 
              src={images[page]} 
              alt="Test" 
              style={{ maxWidth: 200, maxHeight: 150, border: '1px solid #ddd' }}
              onLoad={() => console.log('Direct image loaded successfully')}
              onError={(e) => console.error('Direct image load error:', e)}
            />
          </div>
          <div style={{ border: '2px solid #ddd', borderRadius: '8px', padding: '16px', backgroundColor: '#f9f9f9' }}>
            <div style={{ marginBottom: '12px', fontSize: '14px', fontWeight: 'bold' }}>
              Drag to Select Question Area (like macOS screenshot)
            </div>
            <DragCropSelector
              imageUrl={images[page]}
              onCropComplete={handleCropComplete}
              onCropChange={handleCropChange}
            />
          </div>
        </div>
      )}
    </div>
  )
}


