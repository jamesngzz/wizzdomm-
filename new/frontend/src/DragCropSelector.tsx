import React, { useState, useRef, useEffect } from 'react'

interface DragCropSelectorProps {
  imageUrl: string
  onCropComplete: (bbox: { x: number; y: number; width: number; height: number }) => void
  onCropChange?: (bbox: { x: number; y: number; width: number; height: number }) => void
}

interface CropArea {
  x: number
  y: number
  width: number
  height: number
}

export default function DragCropSelector({ imageUrl, onCropComplete, onCropChange }: DragCropSelectorProps) {
  const [imageLoaded, setImageLoaded] = useState(false)
  const [imageDimensions, setImageDimensions] = useState({ width: 0, height: 0 })
  const [cropArea, setCropArea] = useState<CropArea | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [startPoint, setStartPoint] = useState({ x: 0, y: 0 })
  
  const containerRef = useRef<HTMLDivElement>(null)
  const imageRef = useRef<HTMLImageElement>(null)

  const handleImageLoad = () => {
    if (imageRef.current) {
      setImageDimensions({
        width: imageRef.current.naturalWidth,
        height: imageRef.current.naturalHeight
      })
      setImageLoaded(true)
    }
  }

  const getMousePosition = (e: React.MouseEvent) => {
    if (!containerRef.current) return { x: 0, y: 0 }
    
    const rect = containerRef.current.getBoundingClientRect()
    return {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top
    }
  }

  const handleMouseDown = (e: React.MouseEvent) => {
    if (!imageLoaded) return
    
    const point = getMousePosition(e)
    setStartPoint(point)
    setIsDragging(true)
    setCropArea(null)
  }

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging || !imageLoaded) return
    
    const currentPoint = getMousePosition(e)
    
    const newCropArea = {
      x: Math.min(startPoint.x, currentPoint.x),
      y: Math.min(startPoint.y, currentPoint.y),
      width: Math.abs(currentPoint.x - startPoint.x),
      height: Math.abs(currentPoint.y - startPoint.y)
    }
    
    setCropArea(newCropArea)
    
    // Convert to image coordinates and notify parent
    if (onCropChange && imageRef.current) {
      const scaleX = imageRef.current.naturalWidth / imageRef.current.clientWidth
      const scaleY = imageRef.current.naturalHeight / imageRef.current.clientHeight
      
      const imageCropArea = {
        x: Math.round(newCropArea.x * scaleX),
        y: Math.round(newCropArea.y * scaleY),
        width: Math.round(newCropArea.width * scaleX),
        height: Math.round(newCropArea.height * scaleY)
      }
      
      onCropChange(imageCropArea)
    }
  }

  const handleMouseUp = () => {
    if (!isDragging || !cropArea || !imageRef.current) return
    
    setIsDragging(false)
    
    // Convert display coordinates to image coordinates
    const scaleX = imageRef.current.naturalWidth / imageRef.current.clientWidth
    const scaleY = imageRef.current.naturalHeight / imageRef.current.clientHeight
    
    const imageCropArea = {
      x: Math.round(cropArea.x * scaleX),
      y: Math.round(cropArea.y * scaleY),
      width: Math.round(cropArea.width * scaleX),
      height: Math.round(cropArea.height * scaleY)
    }
    
    // Only call onCropComplete if the selection has some area
    if (imageCropArea.width > 10 && imageCropArea.height > 10) {
      onCropComplete(imageCropArea)
    }
  }

  // Reset crop area when image changes
  useEffect(() => {
    setCropArea(null)
    setImageLoaded(false)
  }, [imageUrl])

  return (
    <div 
      ref={containerRef}
      style={{ 
        position: 'relative', 
        display: 'inline-block',
        cursor: imageLoaded ? 'crosshair' : 'default',
        userSelect: 'none'
      }}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
    >
      <img
        ref={imageRef}
        src={imageUrl}
        alt="Crop target"
        style={{
          maxWidth: '100%',
          maxHeight: '80vh',
          display: 'block',
          pointerEvents: 'none'
        }}
        onLoad={handleImageLoad}
        draggable={false}
      />
      
      {/* Crop selection overlay */}
      {cropArea && (
        <div
          style={{
            position: 'absolute',
            left: cropArea.x,
            top: cropArea.y,
            width: cropArea.width,
            height: cropArea.height,
            border: '2px solid #007bff',
            backgroundColor: 'rgba(0, 123, 255, 0.1)',
            pointerEvents: 'none',
            zIndex: 10
          }}
        />
      )}
      
      {/* Dark overlay outside crop area */}
      {cropArea && (
        <>
          {/* Top overlay */}
          <div
            style={{
              position: 'absolute',
              left: 0,
              top: 0,
              right: 0,
              height: cropArea.y,
              backgroundColor: 'rgba(0, 0, 0, 0.5)',
              pointerEvents: 'none',
              zIndex: 5
            }}
          />
          {/* Bottom overlay */}
          <div
            style={{
              position: 'absolute',
              left: 0,
              top: cropArea.y + cropArea.height,
              right: 0,
              bottom: 0,
              backgroundColor: 'rgba(0, 0, 0, 0.5)',
              pointerEvents: 'none',
              zIndex: 5
            }}
          />
          {/* Left overlay */}
          <div
            style={{
              position: 'absolute',
              left: 0,
              top: cropArea.y,
              width: cropArea.x,
              height: cropArea.height,
              backgroundColor: 'rgba(0, 0, 0, 0.5)',
              pointerEvents: 'none',
              zIndex: 5
            }}
          />
          {/* Right overlay */}
          <div
            style={{
              position: 'absolute',
              left: cropArea.x + cropArea.width,
              top: cropArea.y,
              right: 0,
              height: cropArea.height,
              backgroundColor: 'rgba(0, 0, 0, 0.5)',
              pointerEvents: 'none',
              zIndex: 5
            }}
          />
        </>
      )}
      
      {/* Instructions */}
      {imageLoaded && !cropArea && !isDragging && (
        <div
          style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            backgroundColor: 'rgba(0, 0, 0, 0.7)',
            color: 'white',
            padding: '12px 24px',
            borderRadius: '8px',
            fontSize: '14px',
            pointerEvents: 'none',
            zIndex: 15
          }}
        >
          Click and drag to select the question area
        </div>
      )}
    </div>
  )
}
