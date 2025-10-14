import React, { useEffect, useRef, useState } from 'react'

const API = (import.meta as any).env?.VITE_API_URL || 'http://127.0.0.1:8000/api'

type Submission = {
  id: number
  student_name: string
  exam: number
}

type SubmissionItem = {
  id: number
  question_label: string
}

export default function CanvasEditorPage() {
  const [itemId, setItemId] = useState<number | ''>('')
  const [imgUrl, setImgUrl] = useState<string | null>(null)
  const canvasRef = useRef<any>(null)
  const hostRef = useRef<HTMLCanvasElement | null>(null)
  const [status, setStatus] = useState('')
  const fabricRef = useRef<any>(null)
  const [ready, setReady] = useState(false)
  const [canvasInitialized, setCanvasInitialized] = useState(false)
  const [submissions, setSubmissions] = useState<Submission[]>([])
  const [selectedSubmissionId, setSelectedSubmissionId] = useState<number | ''>('')
  const [items, setItems] = useState<SubmissionItem[]>([])

  // Ensure a render occurs even when renderOnAddRemove is false
  const safeRender = (c: any) => {
    if (!c) return
    if (typeof c.requestRenderAll === 'function') c.requestRenderAll()
    else if (typeof c.renderAll === 'function') c.renderAll()
  }

  // Fetch with timeout utility
  const fetchWithTimeout = async (input: RequestInfo | URL, init: RequestInit = {}, timeoutMs = 15000) => {
    const controller = new AbortController()
    const id = setTimeout(() => controller.abort(), timeoutMs)
    try {
      const res = await fetch(input, { ...init, signal: controller.signal })
      return res
    } finally {
      clearTimeout(id)
    }
  }

  // Load image into Fabric via Blob URL for reliability and better timeouts
  const loadFabricImageViaBlob = async (F: any, url: string, timeoutMs = 15000): Promise<any> => {
    const cacheBusted = url.includes('?') ? `${url}&ts=${Date.now()}` : `${url}?ts=${Date.now()}`
    const res = await fetchWithTimeout(cacheBusted, { method: 'GET', cache: 'no-store' }, timeoutMs)
    if (!res.ok) throw new Error(`Image GET failed: ${res.status}`)
    const blob = await res.blob()
    const objectUrl = URL.createObjectURL(blob)
    try {
      return await fromURLCompat(F, objectUrl, { crossOrigin: 'anonymous' }, 10000)
    } finally {
      // Revoke after Fabric has created its internal image object
      setTimeout(() => URL.revokeObjectURL(objectUrl), 0)
    }
  }

  // Fabric v5 uses callback, v6+ returns a Promise. Support both.
  const fromURLCompat = async (F: any, url: string, options: any, timeoutMs = 10000): Promise<any> => {
    const impl = (F?.Image && F.Image.fromURL) || (F?.FabricImage && F.FabricImage.fromURL)
    if (!impl) throw new Error('Fabric fromURL not available')

    const maybePromise = (() => {
      try {
        // Try promise signature first (v6+)
        const result = impl.call(F.Image || F.FabricImage || F, url, options)
        return result
      } catch {
        return undefined
      }
    })()

    if (maybePromise && typeof maybePromise.then === 'function') {
      // Promise API
      return await withTimeout(maybePromise, timeoutMs, 'Fabric fromURL timeout')
    }

    // Callback API fallback (v5)
    return await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('Fabric fromURL timeout')), timeoutMs)
      impl.call(F.Image || F, url, (img: any) => {
        clearTimeout(timer)
        if (!img) return reject(new Error('Fabric returned null image'))
        resolve(img)
      }, options)
    })
  }

  const withTimeout = async <T,>(p: Promise<T>, ms: number, msg: string): Promise<T> => {
    let timer: any
    const t = new Promise<never>((_, reject) => { timer = setTimeout(() => reject(new Error(msg)), ms) })
    try {
      return await Promise.race([p, t]) as T
    } finally {
      clearTimeout(timer)
    }
  }

  // Load submissions on mount
  useEffect(() => {
    fetch(`${API}/submissions/`)
      .then(r => r.json())
      .then(setSubmissions)
      .catch(e => console.error('Failed to load submissions:', e))
  }, [])

  // Load items when submission is selected
  useEffect(() => {
    if (!selectedSubmissionId) {
      setItems([])
      return
    }
    fetch(`${API}/submissions/${selectedSubmissionId}/grading_summary/`)
      .then(r => r.json())
      .then(data => {
        const itemsList = data.items.map((item: any) => ({
          id: item.item_id,
          question_label: item.question.label
        }))
        setItems(itemsList)
      })
      .catch(e => {
        console.error('Failed to load items:', e)
        setItems([])
      })
  }, [selectedSubmissionId])

  useEffect(() => {
    let disposed = false
    
    const initCanvas = async () => {
      try {
      setStatus('Loading canvas...')
      
      // Pre-load Fabric.js with timeout
      const fabricPromise = import('fabric')
      const timeoutPromise = new Promise((_, reject) => 
        setTimeout(() => reject(new Error('Fabric.js loading timeout (10s)')), 10000)
      )
      
      const mod: any = await Promise.race([fabricPromise, timeoutPromise])
      
      const F = mod.fabric || mod.default?.fabric || mod.default || mod
      
      if (!F || !F.Canvas) {
        const errorMsg = 'Fabric.js Canvas constructor not found in module'
        setStatus(`❌ ${errorMsg}`)
        setReady(false)
        return
      }
      
      fabricRef.current = F
      setStatus('Creating canvas instance...')
      
      // Dispose any existing canvas first
      if (canvasRef.current && canvasRef.current.dispose) canvasRef.current.dispose()
      
      // Create canvas with optimized settings
      const c = new F.Canvas(hostRef.current, { 
        preserveObjectStacking: true,
        width: 800,
        height: 600,
        enableRetinaScaling: false,
        imageSmoothingEnabled: true,
        renderOnAddRemove: false
      })
      
      canvasRef.current = c
      setCanvasInitialized(true)
      
      setReady(true)
      setStatus('✅ Canvas ready! Select a submission and question to start annotating.')
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : String(error)
      setStatus(`❌ Canvas initialization failed: ${errorMsg}`)
      setReady(false)
      }
    }
    
    // Simple initialization - wait for canvas element to be available
    if (hostRef.current) {
      initCanvas()
    } else {
      const checkInterval = setInterval(() => {
        if (disposed) {
          clearInterval(checkInterval)
          return
        }
        
        if (hostRef.current) {
          clearInterval(checkInterval)
          initCanvas()
        }
      }, 50)
      
      // Cleanup interval after 5 seconds
      setTimeout(() => {
        if (!disposed) {
          clearInterval(checkInterval)
          if (!hostRef.current) setStatus('❌ Canvas element not found - please refresh the page')
        }
      }, 5000)
    }
    
    return () => {
      disposed = true
      if (canvasRef.current) { canvasRef.current.dispose(); canvasRef.current = null }
      fabricRef.current = null
      setReady(false)
      setCanvasInitialized(false)
    }
  }, [])

  const loadItem = async () => {
    if (!itemId) return
    if (!ready || !fabricRef.current || !canvasRef.current) { 
      setStatus('Canvas not ready - please wait for Fabric.js to load'); 
      return 
    }
    
    setStatus('Loading item...')
    try {
      const res = await fetch(`${API}/items/${itemId}/`)
      if (!res.ok) { 
        setStatus(`Failed to load item: ${res.status}`); 
        return 
      }
      const d = await res.json()
      const url = d.answer_image_urls?.[0]
      if (!url) { 
        setStatus('No image found for this item'); 
        return 
      }
      
      // Convert relative URL to absolute URL
      const fullUrl = url.startsWith('http') ? url : `${API.replace('/api', '')}${url}`
      setImgUrl(fullUrl)
      setStatus('Loading image...')

      const c = canvasRef.current!
      const F = fabricRef.current
      c.clear()
      safeRender(c)
      
      // Test if URL is accessible first
      try {
        const testResponse = await fetch(fullUrl, { method: 'HEAD' })
        if (!testResponse.ok) {
          setStatus(`❌ Image not accessible: ${testResponse.status} ${testResponse.statusText}`)
          return
        }
      } catch (error) {
        setStatus(`❌ Cannot access image: ${error}`)
        return
      }
      
      // Prefer loading via Blob/object URL to avoid long hangs and leverage timeouts
      let img: any
      try {
        setStatus('Fetching image data...')
        img = await loadFabricImageViaBlob(F, fullUrl, 15000)
      } catch (e) {
        
        setStatus('Retrying with direct image URL...')
        img = await fromURLCompat(F, fullUrl, { crossOrigin: 'anonymous' }, 10000)
      }

      if (!img) {
        setStatus('❌ Failed to load image: Image object is null. Check if the file exists.')
        return
      }

      // Validate image dimensions
      if (!img.width || !img.height || img.width < 1 || img.height < 1) {
        setStatus('❌ Failed to load image: Invalid image dimensions')
        return
      }

      img.selectable = false
      img.set('isBackground', true)  // Mark as background for filtering
      img.set('evented', false)  // Prevent interaction
      const scale = Math.min(700 / img.width!, 900 / img.height!)
      img.scale(scale)
      c.setWidth(img.width! * scale)
      c.setHeight(img.height! * scale)
      c.add(img)
        
        // Load existing annotations if provided (user annotations)
        if (d.annotations && Array.isArray(d.annotations) && d.annotations.length > 0) {
          let loadedCount = 0
          let failedCount = 0
          
          d.annotations.forEach((obj: any) => {
            try {
              F.util.enlivenObjects([obj], (objects: any[]) => {
                try {
                  if (!objects || objects.length === 0) {
                    console.warn('Enliven produced no objects for:', obj)
                    failedCount++
                    return
                  }
                  objects.forEach(o => c.add(o))
                  loadedCount++
                  safeRender(c)
                } catch (e) {
                  failedCount++
                }
              })
            } catch (e) {
              failedCount++
            }
          })
          
          setTimeout(() => {
            if (failedCount > 0) {
              setStatus(`⚠️ Image loaded with ${loadedCount} annotations (${failedCount} failed to load)`)
            } else {
              setStatus(`✅ Image loaded with ${d.annotations.length} existing annotations!`)
            }
          }, 100)
        } else {
          setStatus('✅ Image loaded - ready to annotate!')
        }

        // Render grading overlays from MIRRORING_SPEC (critical/part errors) as editable textboxes
        const grading = d.grading
        if (grading) {
          try {
            // Build a set of existing text contents to avoid duplicates
            const existingTexts = new Set<string>(
              (c.getObjects() || [])
                .filter((o: any) => typeof o.get === 'function' && (o.type === 'textbox' || o.type === 'text'))
                .map((o: any) => String(o.get('text') || ''))
            )

            const drawText = (text: string, topOffset: number, color: string) => {
              if (!text) return
              // Skip if same text already present (either from saved annotations or previously added)
              if (existingTexts.has(text)) return
              const t = new F.Textbox(text, { left: 10, top: 10 + topOffset, fill: color, fontSize: 16, backgroundColor: '#fff' })
              t.set('isGrading', true) // tag for future logic; included in save
              // editable/selectable by default
              c.add(t)
              existingTexts.add(text)
            }
            if (grading.is_correct === true) drawText('✅ Đúng', 0, '#28a745')
            if (grading.is_correct === false) drawText('❌ Sai', 0, '#dc3545')

            let offset = 24
            const critical = Array.isArray(grading.critical_errors) ? grading.critical_errors : []
            critical.slice(0, 10).forEach((err: any, idx: number) => {
              drawText(`❌ ${err?.phrases?.[0] || err?.description || 'Lỗi nghiêm trọng'}`, offset, '#dc3545')
              offset += 22
            })
            const part = Array.isArray(grading.part_errors) ? grading.part_errors : []
            part.slice(0, 10).forEach((err: any) => {
              drawText(`⚠️ ${err?.phrases?.[0] || err?.description || 'Lỗi nhỏ'}`, offset, '#ff9800')
              offset += 22
            })
            safeRender(c)
          } catch (e) {
            // ignore overlay rendering errors
          }
        }
        
        safeRender(c)
      
    } catch (error) {
      console.error('Error loading item:', error)
      setStatus(`Error: ${error}`)
    }
  }

  const addText = () => {
    if (!ready || !fabricRef.current || !canvasRef.current) { setStatus('Canvas not ready'); return }
    const c = canvasRef.current!
    const F = fabricRef.current
    const t = new F.Textbox('⚠️ Ghi chú', { left: 40, top: 40, fill: '#ff0000', fontSize: 18, backgroundColor: '#fff' })
    c.add(t)
    c.setActiveObject(t)
    c.renderAll()
  }

  const addCircle = () => {
    if (!ready || !fabricRef.current || !canvasRef.current) { setStatus('Canvas not ready'); return }
    const c = canvasRef.current!
    const F = fabricRef.current
    const circle = new F.Circle({ left: 100, top: 100, radius: 30, stroke: '#ff0000', fill: 'rgba(0,0,0,0)', strokeWidth: 2 })
    c.add(circle)
    c.setActiveObject(circle)
    c.renderAll()
  }

  const save = async () => {
    if (!ready || !fabricRef.current || !canvasRef.current) { setStatus('Canvas not ready'); return }
    const c = canvasRef.current!
    // Exclude background image using explicit marker
    const objs = c.getObjects().filter((o: any) => !o.get('isBackground'))
    
    // Validate we have objects to save
    if (objs.length === 0) {
      setStatus('No annotations to save')
      return
    }
    
    const payload = objs
      .filter((o: any) => !o.get('isOverlay'))
      .map((o: any) => o.toObject())
    
    try {
      const res = await fetch(`${API}/items/${itemId}/`, { 
        method: 'PUT', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify({ annotations: payload }) 
      })
      if (!res.ok) { 
        const errorText = await res.text()
        setStatus(`Save failed: ${res.status} - ${errorText}`)
        return 
      }
      setStatus('✅ Saved successfully!')
      setTimeout(() => setStatus('Image loaded - ready to annotate!'), 2000)
    } catch (error) {
      setStatus(`Save error: ${error}`)
      console.error('Save error:', error)
    }
  }

  return (
    <div style={{ padding: 20 }}>
      <style>{`
        @keyframes loading {
          0% { width: 0%; }
          50% { width: 70%; }
          100% { width: 100%; }
        }
      `}</style>
      <h3>Canvas Editor - Annotate Student Answers</h3>
      
      {/* Step 1: Select Submission */}
      <div style={{ marginBottom: 24, padding: 16, backgroundColor: '#f8f9fa', borderRadius: 8 }}>
        <h4 style={{ marginTop: 0 }}>Step 1: Select Submission</h4>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <select 
            value={selectedSubmissionId} 
            onChange={e => setSelectedSubmissionId(Number(e.target.value))}
            style={{ padding: '8px 12px', fontSize: 14, minWidth: 200 }}
          >
            <option value="">-- Select a submission --</option>
            {submissions.map(sub => (
              <option key={sub.id} value={sub.id}>
                {sub.student_name} - Exam {sub.exam} (ID: {sub.id})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Step 2: Select Item */}
      {selectedSubmissionId && (
        <div style={{ marginBottom: 24, padding: 16, backgroundColor: '#e7f3ff', borderRadius: 8 }}>
          <h4 style={{ marginTop: 0 }}>Step 2: Select Question Item to Annotate</h4>
          {items.length === 0 ? (
            <div style={{ color: '#856404', padding: 8, backgroundColor: '#fff3cd', borderRadius: 4 }}>
              No items found. Please map questions to this submission first in the Submissions page.
            </div>
          ) : (
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {items.map(item => (
                <button
                  key={item.id}
                  onClick={() => {
                    setItemId(item.id)
                    // Auto-load the item when selected
                    setTimeout(() => {
                      const loadBtn = document.getElementById('load-btn-canvas')
                      if (loadBtn) loadBtn.click()
                    }, 100)
                  }}
                  style={{
                    padding: '8px 16px',
                    backgroundColor: itemId === item.id ? '#007bff' : '#6c757d',
                    color: 'white',
                    border: 'none',
                    borderRadius: 4,
                    cursor: 'pointer',
                    fontWeight: itemId === item.id ? 'bold' : 'normal'
                  }}
                >
                  Question {item.question_label} (Item #{item.id})
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Step 3: Canvas Editor */}
      {itemId && (
        <div style={{ marginBottom: 16, padding: 16, backgroundColor: '#d4edda', borderRadius: 8 }}>
          <h4 style={{ marginTop: 0 }}>Step 3: Annotate</h4>
          
          {/* Canvas Status */}
          <div style={{ marginBottom: 12, padding: 8, backgroundColor: '#fff', borderRadius: 4, border: '1px solid #ddd' }}>
            <strong>Canvas Status: </strong>
            <span style={{ 
              color: status.includes('ready') ? '#28a745' : 
                     status.includes('not ready') || status.includes('failed') || status.includes('error') ? '#dc3545' : 
                     '#ffc107',
              fontWeight: 'bold'
            }}>
              {status || 'Loading...'}
            </span>
            {imgUrl && (
              <div style={{ marginTop: 4, fontSize: 11, color: '#666', wordBreak: 'break-all' }}>
                <strong>Image URL:</strong> {imgUrl}
              </div>
            )}
          </div>
          
          <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap', alignItems: 'center' }}>
            <button id="load-btn-canvas" onClick={loadItem} style={{ display: 'none' }}>Load</button>
            <button 
              onClick={addText} 
              disabled={!ready}
              style={{ 
                padding: '8px 16px', 
                backgroundColor: ready ? '#17a2b8' : '#6c757d', 
                color: 'white', 
                border: 'none', 
                borderRadius: 4, 
                cursor: ready ? 'pointer' : 'not-allowed',
                opacity: ready ? 1 : 0.6
              }}
            >
              📝 Add Note
            </button>
            <button 
              onClick={addCircle} 
              disabled={!ready}
              style={{ 
                padding: '8px 16px', 
                backgroundColor: ready ? '#ffc107' : '#6c757d', 
                color: ready ? 'black' : 'white', 
                border: 'none', 
                borderRadius: 4, 
                cursor: ready ? 'pointer' : 'not-allowed',
                opacity: ready ? 1 : 0.6
              }}
            >
              ⭕ Add Circle
            </button>
            <button 
              onClick={save} 
              disabled={!ready}
              style={{ 
                padding: '8px 16px', 
                backgroundColor: ready ? '#28a745' : '#6c757d', 
                color: 'white', 
                border: 'none', 
                borderRadius: 4, 
                cursor: ready ? 'pointer' : 'not-allowed', 
                fontWeight: 'bold',
                opacity: ready ? 1 : 0.6
              }}
            >
              💾 Save Annotations
            </button>
          </div>
          
          <div style={{ border: '2px solid #28a745', borderRadius: 4, padding: 8, backgroundColor: 'white', minHeight: 400, position: 'relative' }}>
            <canvas ref={hostRef} style={{ display: 'block' }} />
            {!ready && (
              <div style={{ 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center', 
                height: 400, 
                color: '#6c757d',
                fontSize: 16,
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                backgroundColor: 'rgba(255, 255, 255, 0.9)',
                zIndex: 10
              }}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 32, marginBottom: 12 }}>⚡</div>
                  <div style={{ fontWeight: 'bold', marginBottom: 8 }}>Loading Canvas...</div>
                  <div style={{ fontSize: 12, marginBottom: 16 }}>Initializing Fabric.js library</div>
                  <div style={{ 
                    width: 200, 
                    height: 4, 
                    backgroundColor: '#e9ecef', 
                    borderRadius: 2,
                    overflow: 'hidden'
                  }}>
                    <div style={{ 
                      width: '70%', 
                      height: '100%', 
                      backgroundColor: '#28a745',
                      animation: 'loading 2s ease-in-out infinite'
                    }} />
                  </div>
                  <div style={{ 
                    marginTop: 16, 
                    padding: 8, 
                    backgroundColor: '#fff3cd', 
                    borderRadius: 4,
                    fontSize: 11,
                    color: '#856404'
                  }}>
                    <strong>Debug:</strong> Check browser console (F12) for detailed logs
                  </div>
                </div>
              </div>
            )}
          </div>
          
          <div style={{ marginTop: 8, fontSize: 12, color: '#666' }}>
            💡 Tip: Add notes and circles to mark errors or highlight important parts. Then click "Save Annotations" to save your work.
          </div>
        </div>
      )}
    </div>
  )
}


