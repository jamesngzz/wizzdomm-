# Annotation Persistence Fix

## Problem
When users moved annotations to different positions and clicked save, the changes were not persisting. Upon returning to the page, users had to redo their annotations.

## Root Cause
The original implementation saved annotations in Fabric.js format with **absolute pixel coordinates**. However, when the image was reloaded, it could be scaled differently to fit the canvas, causing the absolute coordinates to be misaligned with the actual image content.

Example:
- Session 1: Image scaled to 800x600px → annotation at (100, 100)
- Session 2: Same image scaled to 1000x750px → annotation still at (100, 100) but this is now in a different position relative to the image content

## Solution

### **Use Normalized Coordinates (0..1) as Source of Truth**

Instead of storing absolute pixel coordinates, we now store coordinates normalized to the range 0..1 relative to the image dimensions. This ensures annotations maintain their position relative to the image content regardless of scaling.

### Technical Implementation

#### 1. **Saving Annotations** (`ItemAnnotationCanvas.tsx`)
```typescript
// Get image dimensions
const imgWidth = bgImg.width! * bgImg.scaleX!;
const imgHeight = bgImg.height! * bgImg.scaleY!;

// Normalize each annotation
const normalized = {
  type: 'textbox', // or 'circle', 'rect'
  x: left / imgWidth,        // 0..1
  y: top / imgHeight,        // 0..1  
  w: width / imgWidth,       // 0..1
  h: height / imgHeight,     // 0..1
  // Type-specific properties
  text: '...',
  fontSize: 16,
  fill: '#ff0000'
};
```

#### 2. **Loading Annotations** (`ItemAnnotationCanvas.tsx`)
```typescript
// Get current image scale
const imgWidth = img.width! * scale;
const imgHeight = img.height! * scale;

// Convert normalized coordinates back to canvas coordinates
for (const ann of annotations) {
  const x = ann.x * imgWidth;        // Denormalize
  const y = ann.y * imgHeight;       // Denormalize
  const w = ann.w * imgWidth;        // Denormalize
  const h = ann.h * imgHeight;       // Denormalize
  
  // Create Fabric.js object with correct coordinates
  const obj = new F.Textbox(ann.text, {
    left: x,
    top: y,
    width: w,
    // ...other properties
  });
  canvas.add(obj);
}
```

#### 3. **PDF Export** (`views.py`)
The backend already expects normalized coordinates and scales them to the PDF page dimensions:
```python
# Normalized coordinates from frontend
nx = float(obj.get('x', 0.0))  # 0..1
ny = float(obj.get('y', 0.0))  # 0..1

# Scale to PDF image space
left = x + nx * dw
top_img_space = ny * dh
```

## Supported Annotation Types

### 1. **Text/Textbox**
- Properties: `text`, `fontSize`, `fill` (color)
- Stored: position (x, y), size (w, h), text content, styling

### 2. **Circle**
- Properties: `radius`, `stroke` (color), `strokeWidth`
- Stored: position (x, y), radius (normalized relative to image width)

### 3. **Rectangle**
- Properties: `stroke` (color), `strokeWidth`
- Stored: position (x, y), size (w, h), styling

## Benefits of This Approach

✅ **Resolution Independence**: Annotations maintain correct position regardless of canvas size
✅ **Zoom Compatibility**: Works correctly even if UI zoom levels change
✅ **Export Accuracy**: PDF export receives coordinates in the same normalized format
✅ **Simpler Data Model**: Single source of truth (no need to store multiple formats)
✅ **Better Maintainability**: Clear separation between storage format and display format

## Testing Checklist

- [ ] Add annotation → Save → Reload page → Verify position is correct
- [ ] Move annotation → Save → Reload page → Verify new position is correct  
- [ ] Resize annotation → Save → Reload page → Verify new size is correct
- [ ] Add multiple annotations → Save → Reload → Verify all persist correctly
- [ ] Export PDF → Verify annotations appear in correct positions
- [ ] Test on different screen sizes/zoom levels

## Technical Stack Used

- **Frontend**: React + TypeScript + Fabric.js v6
- **Backend**: Django + ReportLab (PDF generation)
- **Coordinate System**: Normalized (0..1) for storage, absolute pixels for rendering

## Alternative Approaches Considered

### ❌ Store both normalized AND Fabric.js format
- **Pros**: Potentially faster loading (no conversion needed)
- **Cons**: Data duplication, risk of inconsistency, larger storage

### ❌ Store absolute coordinates with image dimensions
- **Pros**: Simple conversion math
- **Cons**: Requires storing extra metadata, still breaks if image is replaced

### ✅ Store normalized coordinates only (CHOSEN)
- **Pros**: Single source of truth, resolution-independent, simple data model
- **Cons**: Requires conversion on load (negligible performance impact)

## Migration Notes

Existing annotations with old format will fail to load properly. If you have critical existing annotations, you may want to:
1. Export them before updating
2. OR: Add a migration function to convert old format to new format
3. OR: Keep backward compatibility code (more complex)

Currently, the code only supports the new normalized format.

