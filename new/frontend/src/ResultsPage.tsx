import React, { useState } from 'react'

const API = (import.meta as any).env?.VITE_API_URL || 'http://127.0.0.1:8000/api'

type Submission = {
  id: number
  exam: number
  student_name: string
  created_at: string
}

export default function ResultsPage() {
  const [submissionId, setSubmissionId] = useState<number | ''>('')
  const [summary, setSummary] = useState<any>(null)
  const [status, setStatus] = useState('')
  const [pdfUrl, setPdfUrl] = useState<string | null>(null)
  const [clarify, setClarify] = useState('')
  const [submissions, setSubmissions] = useState<Submission[]>([])

  React.useEffect(() => {
    fetch(`${API}/submissions/`)
      .then(r => r.json())
      .then(setSubmissions)
      .catch(e => console.error('Failed to load submissions:', e))
  }, [])

  const loadSummary = async () => {
    if (!submissionId) return
    setStatus('Loading summary...')
    const res = await fetch(`${API}/submissions/${submissionId}/grading_summary/`)
    if (!res.ok) { setStatus(`Failed: ${res.status}`); return }
    const data = await res.json()
    setSummary(data)
    setStatus('')
  }

  const exportPdf = async () => {
    if (!submissionId) return
    setStatus('Exporting...')
    const res = await fetch(`${API}/submissions/${submissionId}/export/`, { method: 'POST' })
    if (!res.ok) { setStatus(`Export failed: ${res.status}`); return }
    const data = await res.json()
    setPdfUrl(data.pdf_url)
    setStatus('Export ready')
  }

  const gradeSubmission = async () => {
    if (!submissionId) return
    setStatus('Grading submission...')
    const res = await fetch(`${API}/submissions/${submissionId}/grade/`, { method: 'POST' })
    if (!res.ok) { setStatus(`Grade failed: ${res.status}`); return }
    const data = await res.json()
    setStatus(`Graded ${data.graded_count} items`)
    await loadSummary()
  }

  const regrade = async () => {
    if (!submissionId || !clarify.trim()) { setStatus('Clarify required'); return }
    setStatus('Regrading...')
    const res = await fetch(`${API}/submissions/${submissionId}/regrade/`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ clarify }) })
    if (!res.ok) { setStatus(`Regrade failed: ${res.status}`); return }
    await loadSummary()
    setStatus('Regraded')
  }

  return (
    <div style={{ padding: 20 }}>
      <h3>Results & Grading</h3>
      <div style={{ display: 'flex', gap: 8, marginBottom: 12, alignItems: 'center' }}>
        <input placeholder="Submission ID" value={submissionId} onChange={e => setSubmissionId(Number(e.target.value))} style={{ width: 130 }} />
        <button onClick={loadSummary}>Load Summary</button>
        <button onClick={gradeSubmission} style={{ backgroundColor: '#28a745', color: 'white', fontWeight: 'bold' }}>Grade Submission</button>
        <button onClick={exportPdf}>Export PDF</button>
        <span style={{ marginLeft: 8, color: status.includes('failed') ? 'red' : '#666' }}>{status}</span>
      </div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <input placeholder="Clarify for regrade" value={clarify} onChange={e => setClarify(e.target.value)} style={{ width: 320 }} />
        <button onClick={regrade}>Regrade with Clarify</button>
      </div>
      {pdfUrl && (
        <div style={{ marginBottom: 12 }}>
          <a href={pdfUrl} target="_blank" rel="noreferrer">Open PDF</a>
        </div>
      )}
      {summary && (
        <div>
          <h4>Submission: {summary.student_name} (#{summary.submission})</h4>
          <div style={{ marginTop: 16 }}>
            {summary.items.map((item: any) => (
              <div key={item.item_id} style={{ 
                marginBottom: 16, 
                padding: 16, 
                border: '1px solid #ddd', 
                borderRadius: 8,
                backgroundColor: item.graded ? (item.is_correct ? '#d4edda' : '#f8d7da') : '#fff3cd'
              }}>
                <div style={{ fontWeight: 'bold', fontSize: 16, marginBottom: 8 }}>
                  Question {item.question.label} (Item #{item.item_id})
                </div>
                
                {!item.graded && (
                  <div style={{ color: '#856404' }}>⚠️ Not graded yet</div>
                )}
                
                {item.graded && (
                  <>
                    <div style={{ marginBottom: 8 }}>
                      <span style={{ fontWeight: 'bold' }}>Result: </span>
                      <span style={{ 
                        padding: '4px 8px', 
                        borderRadius: 4, 
                        backgroundColor: item.is_correct ? '#155724' : '#721c24',
                        color: 'white',
                        fontWeight: 'bold'
                      }}>
                        {item.is_correct ? '✓ CORRECT' : '✗ INCORRECT'}
                      </span>
                      {item.partial_credit && (
                        <span style={{ marginLeft: 8, color: '#856404' }}>
                          (Partial credit: Some steps correct)
                        </span>
                      )}
                    </div>

                    {item.critical_errors && item.critical_errors.length > 0 && (
                      <div style={{ marginTop: 12 }}>
                        <div style={{ fontWeight: 'bold', color: '#721c24', marginBottom: 4 }}>
                          Critical Errors:
                        </div>
                        {item.critical_errors.map((err: any, idx: number) => (
                          <div key={idx} style={{ 
                            marginLeft: 16, 
                            marginBottom: 8,
                            padding: 8,
                            backgroundColor: '#f5c6cb',
                            borderRadius: 4
                          }}>
                            <div style={{ fontWeight: 'bold', fontSize: 14 }}>
                              {err.phrases && err.phrases.length > 0 && err.phrases[0]}
                            </div>
                            <div style={{ fontSize: 13, marginTop: 4 }}>
                              {err.description}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    {item.part_errors && item.part_errors.length > 0 && (
                      <div style={{ marginTop: 12 }}>
                        <div style={{ fontWeight: 'bold', color: '#856404', marginBottom: 4 }}>
                          Minor Errors:
                        </div>
                        {item.part_errors.map((err: any, idx: number) => (
                          <div key={idx} style={{ 
                            marginLeft: 16, 
                            marginBottom: 8,
                            padding: 8,
                            backgroundColor: '#fff3cd',
                            borderRadius: 4
                          }}>
                            <div style={{ fontWeight: 'bold', fontSize: 14 }}>
                              {err.phrases && err.phrases.length > 0 && err.phrases[0]}
                            </div>
                            <div style={{ fontSize: 13, marginTop: 4 }}>
                              {err.description}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </>
                )}
              </div>
            ))}
          </div>
          
          <details style={{ marginTop: 16 }}>
            <summary style={{ cursor: 'pointer', fontWeight: 'bold' }}>Raw JSON</summary>
            <pre style={{ background: '#f6f6f6', padding: 12, marginTop: 8 }}>{JSON.stringify(summary, null, 2)}</pre>
          </details>
        </div>
      )}

      <div style={{ marginTop: 32, borderTop: '2px solid #ddd', paddingTop: 16 }}>
        <h4>All Submissions</h4>
        <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: 12 }}>
          <thead>
            <tr style={{ backgroundColor: '#f6f6f6' }}>
              <th style={{ padding: 8, border: '1px solid #ddd', textAlign: 'left' }}>ID</th>
              <th style={{ padding: 8, border: '1px solid #ddd', textAlign: 'left' }}>Student Name</th>
              <th style={{ padding: 8, border: '1px solid #ddd', textAlign: 'left' }}>Exam ID</th>
              <th style={{ padding: 8, border: '1px solid #ddd', textAlign: 'left' }}>Created At</th>
              <th style={{ padding: 8, border: '1px solid #ddd', textAlign: 'center' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {submissions.map(sub => (
              <tr key={sub.id}>
                <td style={{ padding: 8, border: '1px solid #ddd' }}>{sub.id}</td>
                <td style={{ padding: 8, border: '1px solid #ddd', fontWeight: 'bold' }}>{sub.student_name}</td>
                <td style={{ padding: 8, border: '1px solid #ddd' }}>{sub.exam}</td>
                <td style={{ padding: 8, border: '1px solid #ddd', fontSize: 12 }}>
                  {new Date(sub.created_at).toLocaleString()}
                </td>
                <td style={{ padding: 8, border: '1px solid #ddd', textAlign: 'center' }}>
                  <button 
                    onClick={() => {
                      setSubmissionId(sub.id)
                      setSummary(null)
                      setPdfUrl(null)
                    }}
                    style={{ 
                      padding: '4px 8px', 
                      backgroundColor: submissionId === sub.id ? '#007bff' : '#6c757d',
                      color: 'white',
                      border: 'none',
                      borderRadius: 4,
                      cursor: 'pointer',
                      fontSize: 12
                    }}
                  >
                    {submissionId === sub.id ? 'Selected' : 'Select'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}


