import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Crop, Loader2 } from "lucide-react";

interface CroppingCanvasProps {
  imageUrl: string;
  onCropSave: (cropData: {
    answer_bbox_coordinates: { left: number; top: number; width: number; height: number };
    original_image_dimensions: { width: number; height: number };
  }) => void;
  saving?: boolean;
}

interface CropArea {
  x: number;
  y: number;
  width: number;
  height: number;
}

export const CroppingCanvas = ({ imageUrl, onCropSave, saving = false }: CroppingCanvasProps) => {
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageDimensions, setImageDimensions] = useState({ width: 0, height: 0 });
  const [cropArea, setCropArea] = useState<CropArea | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [startPoint, setStartPoint] = useState({ x: 0, y: 0 });
  
  const containerRef = useRef<HTMLDivElement>(null);
  const imageRef = useRef<HTMLImageElement>(null);

  const handleImageLoad = () => {
    if (imageRef.current) {
      setImageDimensions({
        width: imageRef.current.naturalWidth,
        height: imageRef.current.naturalHeight
      });
      setImageLoaded(true);
    }
  };

  const getMousePosition = (e: React.MouseEvent) => {
    if (!containerRef.current) return { x: 0, y: 0 };
    
    const rect = containerRef.current.getBoundingClientRect();
    return {
      x: e.clientX - rect.left,
      y: e.clientY - rect.top
    };
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    if (!imageLoaded) return;
    
    const point = getMousePosition(e);
    setStartPoint(point);
    setIsDragging(true);
    setCropArea(null);
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging || !imageLoaded) return;
    
    const currentPoint = getMousePosition(e);
    
    const newCropArea = {
      x: Math.min(startPoint.x, currentPoint.x),
      y: Math.min(startPoint.y, currentPoint.y),
      width: Math.abs(currentPoint.x - startPoint.x),
      height: Math.abs(currentPoint.y - startPoint.y)
    };
    
    setCropArea(newCropArea);
  };

  const handleMouseUp = () => {
    if (!isDragging) return;
    setIsDragging(false);
  };

  const handleSaveCrop = () => {
    if (!cropArea || !imageRef.current) return;

    // Convert display coordinates to image coordinates
    const scaleX = imageRef.current.naturalWidth / imageRef.current.clientWidth;
    const scaleY = imageRef.current.naturalHeight / imageRef.current.clientHeight;
    
    const imageCropArea = {
      x: Math.round(cropArea.x * scaleX),
      y: Math.round(cropArea.y * scaleY),
      width: Math.round(cropArea.width * scaleX),
      height: Math.round(cropArea.height * scaleY)
    };

    const cropData = {
      answer_bbox_coordinates: {
        left: imageCropArea.x,
        top: imageCropArea.y,
        width: imageCropArea.width,
        height: imageCropArea.height,
      },
      original_image_dimensions: imageDimensions,
    };

    onCropSave(cropData);
  };

  // Reset crop area when image changes
  useEffect(() => {
    setCropArea(null);
    setImageLoaded(false);
  }, [imageUrl]);

  // Add keyboard handler for Enter key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Enter" && cropArea && !saving) {
        e.preventDefault();
        handleSaveCrop();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [cropArea, saving]);

  return (
    <div className="space-y-4">
      <div className="flex gap-2 items-center">
        <Button onClick={handleSaveCrop} disabled={!cropArea || saving} size="lg">
          {saving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
          {saving ? "Saving..." : "Save Crop"}
        </Button>
        {cropArea && (
          <span className="text-sm text-muted-foreground">Press <kbd className="px-2 py-1 bg-muted rounded border">Enter</kbd> to save</span>
        )}
      </div>
      <div className="border border-border rounded-lg overflow-hidden">
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
              Click and drag to select area, then press Enter to save
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
