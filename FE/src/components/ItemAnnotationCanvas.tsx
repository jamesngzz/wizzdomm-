import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Type, Circle as CircleIcon, Square, Save, Loader2, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { getItemDetail, updateItemAnnotations, API_BASE } from "@/lib/api";
import type { ItemDetail } from "@/lib/types";

interface ItemAnnotationCanvasProps {
  itemId: number;
  onSaved?: () => void;
  onVisiblePageChange?: (pageIndex: number) => void;
}

export const ItemAnnotationCanvas = ({ itemId, onSaved, onVisiblePageChange }: ItemAnnotationCanvasProps) => {
  const canvasRef = useRef<any>(null);
  const hostRef = useRef<HTMLCanvasElement | null>(null);
  const fabricRef = useRef<any>(null);
  type PageMeta = { w: number; h: number; offsetY: number };
  const pagesRef = useRef<PageMeta[]>([]);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  
  const [ready, setReady] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [itemData, setItemData] = useState<ItemDetail | null>(null);
  const [status, setStatus] = useState("Initializing canvas...");
  // No explicit page index for stacked render
  // Emoji-to-glyph sanitizer and math normalization
  const normalizeMathText = (raw: string | undefined | null): string => {
    if (!raw) return "";
    let text = String(raw);
    // Replace emoji icons
    text = text.split("✅").join("✓").split("❌").join("✗")
               .split("⚠️").join("!").split("⚠").join("!");
    // Strip LaTeX delimiters $ ... $ and \( ... \)
    text = text.replace(/\\\(|\\\)/g, "");
    text = text.replace(/\$/g, "");
    // Use true minus
    text = text.replace(/-/g, "−");
    // Superscript digits after caret ^
    const supMap: Record<string, string> = { '0':'⁰','1':'¹','2':'²','3':'³','4':'⁴','5':'⁵','6':'⁶','7':'⁷','8':'⁸','9':'⁹' };
    text = text.replace(/\^(\d+)/g, (_m, d: string) => d.split("").map(ch => supMap[ch] || ch).join(""));
    return text;
  };

  const sanitizeText = (text: string | undefined | null): string => normalizeMathText(text);

  // Safe render helper
  const safeRender = (c: any) => {
    if (!c) return;
    if (typeof c.requestRenderAll === "function") c.requestRenderAll();
    else if (typeof c.renderAll === "function") c.renderAll();
  };

  // Timeout utility
  const withTimeout = async <T,>(p: Promise<T>, ms: number, msg: string): Promise<T> => {
    let timer: any;
    const t = new Promise<never>((_, reject) => {
      timer = setTimeout(() => reject(new Error(msg)), ms);
    });
    try {
      return (await Promise.race([p, t])) as T;
    } finally {
      clearTimeout(timer);
    }
  };

  // Determine which page is currently in view within the scroll container
  const getVisiblePageIndex = (): number => {
    const container = scrollRef.current;
    const pages = pagesRef.current;
    if (!container || pages.length === 0) return 0;
    const mid = container.scrollTop + container.clientHeight / 2;
    for (let i = 0; i < pages.length; i++) {
      const m = pages[i];
      const bandEnd = m.offsetY + m.h + 20; // include gap
      if (mid >= m.offsetY && mid < bandEnd) return i;
    }
    return 0;
  };

  // Initialize Fabric.js canvas
  useEffect(() => {
    let disposed = false;

    const initCanvas = async () => {
      try {
        setStatus("Loading canvas library...");

        // Fabric.js v6+ uses direct imports
        const fabricModule: any = await import("fabric");
        
        // In v6, everything is exported directly
        if (!fabricModule || !fabricModule.Canvas) {
          setStatus("❌ Fabric.js Canvas not found");
          setReady(false);
          return;
        }

        fabricRef.current = fabricModule;
        setStatus("Creating canvas...");

        if (canvasRef.current && canvasRef.current.dispose) {
          canvasRef.current.dispose();
        }

        const c = new fabricModule.Canvas(hostRef.current, {
          preserveObjectStacking: true,
          width: 800,
          height: 600,
          enableRetinaScaling: false,
          imageSmoothingEnabled: true,
          renderOnAddRemove: false,
        });

        canvasRef.current = c;
        setReady(true);
        setStatus("✅ Canvas ready");
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : String(error);
        setStatus(`❌ Canvas initialization failed: ${errorMsg}`);
        setReady(false);
      }
    };

    if (hostRef.current) {
      initCanvas();
    }

    return () => {
      disposed = true;
      if (canvasRef.current) {
        canvasRef.current.dispose();
        canvasRef.current = null;
      }
      fabricRef.current = null;
      setReady(false);
    };
  }, []);

  // Load item data and stack all images vertically
  useEffect(() => {
    if (!itemId || !ready || !fabricRef.current || !canvasRef.current) return;

    const loadItem = async () => {
      setLoading(true);
      setStatus("Loading item...");
      
      try {
        const data = await getItemDetail(itemId);
        setItemData(data);

        const urls = Array.isArray(data.answer_image_urls) ? data.answer_image_urls : [];
        if (!urls.length) {
          setStatus("No image found for this item");
          setLoading(false);
          return;
        }
        setStatus("Loading images...");

        const c = canvasRef.current!;
        const F = fabricRef.current;
        c.clear();
        safeRender(c);

        // Stack all images
        const metas: PageMeta[] = [];
        let offsetY = 0;
        let maxW = 0;
        for (const u of urls) {
          let img: any;
          try {
            img = await withTimeout(
              F.FabricImage.fromURL(u, { crossOrigin: "anonymous" }),
              15000,
              "Image loading timeout"
            );
          } catch (e) {
            console.error("Failed to load image:", u, e);
            continue;
          }
          if (!img || !img.width || !img.height || img.width < 1 || img.height < 1) continue;
          const scale = Math.min(700 / img.width!, 900 / img.height!);
          img.scale(scale);
          img.selectable = false;
          img.set("isBackground", true);
          img.set("evented", false);
          const w = img.width! * scale;
          const h = img.height! * scale;
          img.set({ left: 0, top: offsetY });
          metas.push({ w, h, offsetY });
          if (w > maxW) maxW = w;
          offsetY += h + 20; // gap
          c.add(img);
        }
        if (!metas.length) {
          setStatus("❌ Failed to load images");
          setLoading(false);
          return;
        }
        pagesRef.current = metas;
        c.setWidth(maxW);
        c.setHeight(metas[metas.length - 1].offsetY + metas[metas.length - 1].h);

        // Load existing annotations from normalized coordinates
        if (data.annotations && Array.isArray(data.annotations) && data.annotations.length > 0) {
          try {
            console.log(`Loading ${data.annotations.length} existing annotations:`, data.annotations);
            let loadedCount = 0;
            
            // Process annotations sequentially to avoid async issues
            for (const annotation of data.annotations) {
              const ann = annotation as any; // Type assertion for flexibility
              
              // Check if it's normalized format (new) or Fabric.js format (old)
              const isNormalizedFormat = ('x' in ann && 'y' in ann && 'w' in ann && 'h' in ann);
              const isFabricFormat = ('left' in ann && 'top' in ann && 'width' in ann && 'height' in ann);
              
              console.log(`Processing annotation: type=${ann.type}, normalized=${isNormalizedFormat}, fabric=${isFabricFormat}`);
              
              if (isNormalizedFormat) {
                // New normalized format
                const type = ann.type;
                const page = typeof ann.page === 'number' ? ann.page : 0;
                const meta = pagesRef.current[page] || pagesRef.current[0];
                const x = (ann.x || 0) * meta.w;
                const y = meta.offsetY + (ann.y || 0) * meta.h;
                const w = (ann.w || 0) * meta.w;
                const h = (ann.h || 0) * meta.h;

                let obj: any = null;

                if (type === 'textbox' || type === 'text') {
                  obj = new F.Textbox(sanitizeText(ann.text || ''), {
                    left: x,
                    top: y,
                    width: w,
                    fill: ann.fill || '#ff0000',
                    fontSize: ann.fontSize || 16,
                    fontFamily: 'Helvetica, Arial, sans-serif',
                    lineHeight: 1.2,
                    textAlign: ann.textAlign || 'left',
                    backgroundColor: '#fff',
                    editable: true,
                    selectable: true,
                    evented: true,
                  });
                  const annPage = typeof ann.page === 'number' ? ann.page : 0;
                  try { obj.set('page', annPage); } catch {}
                } else if (type === 'circle') {
                  // For circle, radius is normalized relative to image width
                  const radius = (ann.radius || 0.05) * (pagesRef.current[(typeof ann.page==='number'?ann.page:0)]?.w || pagesRef.current[0].w);
                  obj = new F.Circle({
                    left: x,
                    top: y,
                    radius: radius,
                    stroke: ann.stroke || '#ff0000',
                    fill: 'transparent',
                    strokeWidth: ann.strokeWidth || 2,
                  });
                } else if (type === 'rect') {
                  obj = new F.Rect({
                    left: x,
                    top: y,
                    width: w,
                    height: h,
                    stroke: ann.stroke || '#ff0000',
                    fill: 'transparent',
                    strokeWidth: ann.strokeWidth || 2,
                  });
                  const annPage = typeof ann.page === 'number' ? ann.page : 0;
                  try { (obj as any).set('page', annPage); } catch {}
                }

                if (obj) {
                  c.add(obj);
                  loadedCount++;
                  console.log(`Added normalized annotation: ${type} at (${x}, ${y})`);
                }
              } else if (isFabricFormat) {
                // Old Fabric.js format - try to restore directly
                try {
                  const obj = await F.util.enlivenObjects([ann]);
                  if (obj && obj[0]) {
                    // Sanitize any emoji icons in restored Fabric objects
                    try {
                      const current = obj[0].get && obj[0].get('text');
                      if (typeof current === 'string' && current) {
                        const cleaned = sanitizeText(current);
                        if (cleaned !== current) obj[0].set('text', cleaned);
                      }
                    } catch {}
                    c.add(obj[0]);
                    loadedCount++;
                    console.log(`Added Fabric.js annotation: ${ann.type}`);
                  }
                } catch (e) {
                  console.error('Failed to restore Fabric.js annotation:', e);
                }
              } else {
                console.log('Skipping annotation - unrecognized format:', Object.keys(ann));
              }
            }
            
            console.log(`Successfully loaded ${loadedCount} out of ${data.annotations.length} annotations`);
            
            // Status header (✓/✗ Q...) is permanently disabled by request
            
            setStatus(`✅ Image loaded with ${loadedCount} annotations`);
          } catch (e) {
            console.error("Failed to load annotations:", e);
            setStatus("⚠️ Image loaded but annotations failed to load");
          }
        } else {
          // No saved annotations yet. If grading exists, generate initial annotations ONCE and autosave.
          const grading = data.grading;
          if (grading) {
            try {
              const gen: any[] = [];
              const meta0 = pagesRef.current[0];
              const marginX = 0.02 * meta0.w; // pixels
              let cursorY = meta0.offsetY + 0.02 * meta0.h; // pixels
              const maxWidthPx = 0.6 * meta0.w;
              const baseFontSize = 16;
              const lineHeight = 1.2;

              const pushLine = (text: string, color: string) => {
                const clean = sanitizeText(text);
                const hPx = baseFontSize * lineHeight;
                const obj = {
                  type: 'textbox',
                  x: marginX / meta0.w,
                  y: (cursorY - meta0.offsetY) / meta0.h,
                  w: maxWidthPx / meta0.w,
                  h: hPx / meta0.h,
                  text: clean,
                  fontSize: baseFontSize,
                  fill: color,
                  fontFamily: 'Helvetica, Arial, sans-serif',
                  lineHeight: lineHeight,
                  textAlign: 'left',
                  page: 0,
                };
                gen.push(obj);
                cursorY += hPx + 6; // small gap
              };

              // Status line first
              if (grading.is_correct === true) pushLine('✓ đúng', '#28a745');
              else if (grading.is_correct === false) pushLine('✗ sai', '#dc3545');

              const critical = Array.isArray(grading.critical_errors) ? grading.critical_errors : [];
              critical.slice(0, 10).forEach((err: any) => {
                const text = err?.phrases?.[0] || err?.description || 'Lỗi nghiêm trọng';
                pushLine(`✗ ${text}`, '#dc3545');
              });

              const part = Array.isArray(grading.part_errors) ? grading.part_errors : [];
              part.slice(0, 10).forEach((err: any) => {
                const text = err?.phrases?.[0] || err?.description || 'Partial error';
                pushLine(`! ${text}`, '#ff9800');
              });

              if (gen.length > 0) {
                setStatus('Autosaving generated annotations...');
                try {
                  await updateItemAnnotations(itemId, gen);
                  setStatus(`✅ Generated ${gen.length} annotations`);
                  // Render them immediately on canvas
                  for (const ann of gen) {
                    const obj = new F.Textbox(ann.text, {
                      left: ann.x * meta0.w,
                      top: meta0.offsetY + ann.y * meta0.h,
                      width: ann.w * meta0.w,
                      fill: ann.fill,
                      fontSize: ann.fontSize,
                      fontFamily: ann.fontFamily,
                      lineHeight: ann.lineHeight,
                      textAlign: ann.textAlign,
                      backgroundColor: '#fff',
                      editable: true,
                      selectable: true,
                      evented: true,
                    });
                    try { (obj as any).set('page', 0); } catch {}
                    c.add(obj);
                  }
                } catch (e) {
                  console.error('Autosave generated annotations failed:', e);
                }
              } else {
                setStatus('✅ Image loaded - ready to annotate!');
              }
            } catch (e) {
              console.error('Generate-once annotations failed:', e);
              setStatus('✅ Image loaded - ready to annotate!');
            }
          } else {
            setStatus("✅ Image loaded - ready to annotate!");
          }
        }

        // When objects are modified, update their page according to vertical position
        try {
          c.off && c.off('object:modified');
        } catch {}
        c.on('object:modified', (evt: any) => {
          const o = evt?.target;
          if (!o || (o.get && o.get('isBackground'))) return;
          const centerY = (o.top || 0) + ((o.height || 0) * (o.scaleY || 1)) / 2;
          for (let i = 0; i < pagesRef.current.length; i++) {
            const m = pagesRef.current[i];
            if (centerY >= m.offsetY && centerY < m.offsetY + m.h + 20) {
              try { o.set('page', i); } catch {}
              break;
            }
          }
        });

        // Stop auto-generating overlays: from now on, only user-saved annotations are rendered

        safeRender(c);
        setLoading(false);
      } catch (error) {
        console.error("Error loading item:", error);
        setStatus(`Error: ${error}`);
        setLoading(false);
        toast.error("Failed to load item");
      }
    };

    loadItem();
  }, [itemId, ready]);

  // Emit visible page index on scroll
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const handler = () => {
      const idx = getVisiblePageIndex();
      if (onVisiblePageChange) onVisiblePageChange(idx);
    };
    // fire once
    handler();
    el.addEventListener('scroll', handler, { passive: true });
    return () => {
      el.removeEventListener('scroll', handler as any);
    };
  }, [onVisiblePageChange]);

  const addText = () => {
    if (!ready || !fabricRef.current || !canvasRef.current) {
      toast.error("Canvas not ready");
      return;
    }
    const c = canvasRef.current!;
    const F = fabricRef.current;
    const pageIdx = getVisiblePageIndex();
    const meta = pagesRef.current[pageIdx] || pagesRef.current[0];
    const t = new F.Textbox(sanitizeText("⚠️ Note"), {
      left: 40,
      top: meta.offsetY + 40,
      fill: "#ff0000",
      fontSize: 18,
      fontFamily: 'Helvetica, Arial, sans-serif',
      lineHeight: 1.2,
      textAlign: 'left',
      backgroundColor: "#fff",
      editable: true,
    });
    try { (t as any).set('page', pageIdx); } catch {}
    c.add(t);
    c.setActiveObject(t);
    c.renderAll();
    toast.success("Text added - click to edit");
  };

  const addCircle = () => {
    if (!ready || !fabricRef.current || !canvasRef.current) {
      toast.error("Canvas not ready");
      return;
    }
    const c = canvasRef.current!;
    const F = fabricRef.current;
    const pageIdx = getVisiblePageIndex();
    const meta = pagesRef.current[pageIdx] || pagesRef.current[0];
    const circle = new F.Circle({
      left: 100,
      top: meta.offsetY + 100,
      radius: 30,
      stroke: "#ff0000",
      fill: "transparent",
      strokeWidth: 2,
    });
    try { (circle as any).set('page', pageIdx); } catch {}
    c.add(circle);
    c.setActiveObject(circle);
    c.renderAll();
    toast.success("Circle added - drag to position");
  };

  const addRect = () => {
    if (!ready || !fabricRef.current || !canvasRef.current) {
      toast.error("Canvas not ready");
      return;
    }
    const c = canvasRef.current!;
    const F = fabricRef.current;
    const pageIdx = getVisiblePageIndex();
    const meta = pagesRef.current[pageIdx] || pagesRef.current[0];
    const rect = new F.Rect({
      left: 100,
      top: meta.offsetY + 100,
      width: 80,
      height: 60,
      stroke: "#ff0000",
      fill: "transparent",
      strokeWidth: 2,
    });
    try { (rect as any).set('page', pageIdx); } catch {}
    c.add(rect);
    c.setActiveObject(rect);
    c.renderAll();
    toast.success("Rectangle added - drag to position");
  };

  const save = async () => {
    if (!ready || !fabricRef.current || !canvasRef.current) {
      toast.error("Canvas not ready");
      return;
    }

    const c = canvasRef.current!;
    const allObjs = c.getObjects();
    console.log("All canvas objects:", allObjs.map((o: any) => ({
      type: o.type,
      isBackground: o.get("isBackground"),
      isOverlay: o.get("isOverlay"),
      isGrading: o.get("isGrading")
    })));

    const objs = allObjs.filter((o: any) => !o.get("isBackground"));
    console.log(`Filtered objects (non-background): ${objs.length}`);

    if (objs.length === 0) {
      toast.error("No annotations to save");
      return;
    }

    // We no longer infer page from Y; rely on explicit object 'page' (default 0)

    // Normalize annotations to 0..1 relative to image dimensions
    console.log("Objects before filtering:", objs.map((o: any) => ({
      type: o.type,
      isGrading: o.get && o.get("isGrading"),
      isOverlay: o.get && o.get("isOverlay"),
      isBackground: o.get && o.get("isBackground"),
      left: o.left,
      top: o.top
    })));
    
    const filteredObjs = objs.filter((o: any) => {
      const isBackground = o.get && o.get("isBackground");
      // No overlays anymore, just exclude background
      const shouldInclude = !isBackground;
      return shouldInclude;
    });
    
    console.log(`Filtered ${objs.length} objects down to ${filteredObjs.length}`);
    
    const payload = filteredObjs.map((o: any) => {
        const type = o.type;
        // Determine page meta from explicit object property (default 0)
        let objPage = 0;
        try {
          const maybe = o.get && o.get('page');
          if (typeof maybe === 'number') objPage = maybe;
        } catch {}
        const meta = pagesRef.current[objPage] || pagesRef.current[0];
        const left = o.left || 0;
        const top = (o.top || 0) - meta.offsetY;
        const width = (o.width || 0) * (o.scaleX || 1);
        const height = (o.height || 0) * (o.scaleY || 1);
        // Normalize to 0..1 relative to page dimensions
        const normalized: any = {
          type: type,
          x: left / meta.w,
          y: top / meta.h,
          w: width / meta.w,
          h: height / meta.h,
          page: objPage,
        };

        // Add type-specific properties
        if (type === 'textbox' || type === 'text') {
          normalized.text = o.text || '';
          normalized.fontSize = o.fontSize || 16;
          normalized.fill = o.fill || '#ff0000';
          // Persist exact layout for PDF parity
          try {
            normalized.fontFamily = o.fontFamily || 'Helvetica, Arial, sans-serif';
            normalized.lineHeight = o.lineHeight || 1.2;
            normalized.textAlign = o.textAlign || 'left';
            // Fabric v6 stores computed lines in _textLines as array of graphemes
            if (o._textLines && Array.isArray(o._textLines) && o._textLines.length) {
              const lines = o._textLines.map((ln: any) => {
                if (Array.isArray(ln)) {
                  // join graphemes without commas
                  return sanitizeText(ln.map((ch: any) => (typeof ch === 'string' ? ch : String(ch))).join(''));
                }
                return sanitizeText(typeof ln === 'string' ? ln : String(ln));
              });
              if (lines && lines.length) normalized.lines = lines;
            }
          } catch {}
        } else if (type === 'circle') {
          // Normalize radius relative to image width for consistency
          normalized.radius = ((o.radius || 0) * (o.scaleX || 1)) / meta.w;
          normalized.stroke = o.stroke || '#ff0000';
          normalized.strokeWidth = o.strokeWidth || 2;
        } else if (type === 'rect') {
          normalized.stroke = o.stroke || '#ff0000';
          normalized.strokeWidth = o.strokeWidth || 2;
        }

        return normalized;
      });

    console.log(`Saving ${payload.length} annotations:`, JSON.stringify(payload, null, 2));

    setSaving(true);
    try {
      await updateItemAnnotations(itemId, payload);
      console.log("Save successful!");
      toast.success("Annotations saved!");
      setStatus("✅ Saved successfully!");
      if (onSaved) onSaved();
    } catch (error) {
      console.error("Save error:", error);
      toast.error("Failed to save annotations");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Status Bar */}
      <div className="flex items-center justify-between p-3 bg-muted/50 rounded-lg border">
        <div className="flex items-center gap-2">
          <div
            className={`h-2 w-2 rounded-full ${ready ? "bg-green-500" : "bg-yellow-500"}`}
          />
          <span className="text-sm font-medium">{status}</span>
        </div>
        {itemData && (
          <span className="text-xs text-muted-foreground">Question {itemData.question_label}</span>
        )}
      </div>

      {/* Canvas area with sticky top toolbar */}
      <div ref={scrollRef} className="border border-border rounded-lg overflow-auto bg-muted/10 relative min-h-[400px] max-h-[80vh]">
        {/* Sticky toolbar */}
        <div className="sticky top-0 z-10 flex items-center gap-2 border-b border-border bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60 p-2">
          <Button onClick={addText} disabled={!ready || loading} variant="outline" size="icon" title="Add note">
            <Type className="h-4 w-4" />
          </Button>
          <Button
            onClick={() => {
              if (!ready || !canvasRef.current) return;
              const c = canvasRef.current!;
              const selected = c.getActiveObjects() || [];
              const toDelete = selected.filter((o: any) => !o.get("isBackground") && !o.get("isOverlay") && !o.get("isGrading"));
              toDelete.forEach((o: any) => c.remove(o));
              if (toDelete.length > 0) {
                c.discardActiveObject();
                c.requestRenderAll();
                toast.success(`Deleted ${toDelete.length} annotation(s)`);
              } else {
                toast.info("Select annotation(s) to delete");
              }
            }}
            disabled={!ready || loading}
            variant="outline"
            size="icon"
            title="Delete selected"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
          <Button onClick={addCircle} disabled={!ready || loading} variant="outline" size="icon" title="Add circle">
            <CircleIcon className="h-4 w-4" />
          </Button>
          <Button onClick={addRect} disabled={!ready || loading} variant="outline" size="icon" title="Add rectangle">
            <Square className="h-4 w-4" />
          </Button>
          <Button onClick={save} disabled={!ready || loading || saving} size="icon" title="Save annotations">
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
          </Button>
        </div>

        {/* Canvas */}
        <div className="p-4">
          <canvas ref={hostRef} className="mx-auto" />
        </div>

        {!ready && (
          <div className="absolute inset-0 flex items-center justify-center bg-background/80">
            <div className="text-center space-y-2">
              <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary" />
              <p className="text-sm text-muted-foreground">Loading canvas...</p>
            </div>
          </div>
        )}
        {loading && ready && (
          <div className="absolute inset-0 flex items-center justify-center bg-background/80">
            <div className="text-center space-y-2">
              <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary" />
              <p className="text-sm text-muted-foreground">Loading image...</p>
            </div>
          </div>
        )}
      </div>

      <p className="text-xs text-muted-foreground px-1">
        💡 Add notes, circles, and rectangles. Select objects to delete. Save when done.
      </p>
    </div>
  );
};

