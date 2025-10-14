import { useEffect, useMemo, useState, useCallback } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Crop, CheckCircle, Loader2, ChevronLeft, ChevronRight, Trash2, ZoomIn } from "lucide-react";
import { CroppingCanvas } from "@/components/CroppingCanvas";
import { toast } from "sonner";
import { useNavigate, useSearchParams } from "react-router-dom";
import { createSubmissionItem, getSubmission, getSubmissionImages, listExamQuestions, gradingSummary, getSubmissionItemsList, deleteSubmissionItem, gradeItem, gradeSubmission, appendSubmissionItemImage } from "@/lib/api";
import { useWebSocket } from "@/hooks/use-websocket";

type CropStatus = "pending" | "done" | "grading";

const CropSubmission = () => {
  const navigate = useNavigate();
  const [sp] = useSearchParams();
  const submissionId = Number(sp.get("submissionId"));

  const [studentName, setStudentName] = useState<string>("");
  const [questions, setQuestions] = useState<Array<{ id: number; label: string; status: CropStatus; itemId?: number; imageUrls?: string[] }>>([]);
  const [selectedQuestionId, setSelectedQuestionId] = useState<number | null>(null);
  const [images, setImages] = useState<string[]>([]);
  const [pageIndex, setPageIndex] = useState(0);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [previewImageUrl, setPreviewImageUrl] = useState<string | null>(null);
  const [gradingStartByQuestionId, setGradingStartByQuestionId] = useState<Record<number, number>>({});
  const [gradedQuestionIds, setGradedQuestionIds] = useState<Set<number>>(new Set());
  const [tick, setTick] = useState(0);

  const currentImage = useMemo(() => images[pageIndex] || "", [images, pageIndex]);

  // Polling fallback to check grading status
  const checkGradingStatus = useCallback(async () => {
    if (!submissionId) return;
    try {
      const summary = await gradingSummary(submissionId);
      if (summary && summary.items) {
        // Track which questions are graded according to backend
        const gradedIds = new Set<number>((summary.items || []).filter((i: any) => i.graded).map((i: any) => i.question.id));
        setGradedQuestionIds(gradedIds);
        setQuestions((prev) =>
          prev.map((q) => {
            const item = summary.items.find((i: any) => i.question.id === q.id);
            if (item && item.graded && q.status === "grading") {
              // Clear grading timer once graded
              const { [q.id]: _, ...rest } = gradingStartByQuestionId;
              setGradingStartByQuestionId(rest);
              return { ...q, status: "done" as CropStatus };
            }
            return q;
          })
        );
      }
    } catch (e) {
      console.error("Failed to check grading status:", e);
    }
  }, [submissionId, gradingStartByQuestionId]);

  // WebSocket connection for real-time updates
  const handleWebSocketMessage = useCallback((msg: any) => {
    console.log("WebSocket message received:", msg);
    if (msg.event === "GRADE_ITEM" && msg.status === "succeeded") {
      toast.success("Grading completed!");
      checkGradingStatus();
    }
  }, [checkGradingStatus]);

  const { connected } = useWebSocket(handleWebSocketMessage);

  // Polling fallback - check every 5 seconds if there are grading items
  useEffect(() => {
    const hasGrading = questions.some((q) => q.status === "grading");
    if (!hasGrading) return;

    const interval = setInterval(() => {
      checkGradingStatus();
    }, 5000);

    return () => clearInterval(interval);
  }, [questions, checkGradingStatus]);

  // Local 1s tick while any question is grading to update the on-card timer
  useEffect(() => {
    const hasGrading = questions.some((q) => q.status === "grading");
    if (!hasGrading) return;
    const id = setInterval(() => setTick((t) => t + 1), 1000);
    return () => clearInterval(id);
  }, [questions]);

  useEffect(() => {
    if (!submissionId || isNaN(submissionId) || submissionId <= 0) {
      return;
    }
    let mounted = true;
    (async () => {
      try {
        setLoading(true);
        const [sub, imgs] = await Promise.all([
          getSubmission(submissionId),
          getSubmissionImages(submissionId),
        ]);
        if (!mounted) return;
        
        if (!sub) {
          throw new Error("Submission data is null or undefined");
        }
        if (!imgs) {
          throw new Error("Images data is null or undefined");
        }
        
        setStudentName(sub.student_name || "Unknown Student");
        try {
          const label = `${sub.student_name || ''} • #${submissionId}`.trim();
          window.dispatchEvent(new CustomEvent("ta:update-crop-tab", { detail: { id: submissionId, label } }));
        } catch {}
        setImages(imgs.urls || []);
        setPageIndex(0);
        
        // Fetch questions and their submission items
        const qRes = await listExamQuestions(sub.exam);
        if (!mounted) return;
        
        // Fetch submission items to see which questions have answer images
        const itemsList = await getSubmissionItemsList(submissionId);
        if (!mounted) return;
        
        const mapped = (qRes.items || []).map((it: any) => {
          const item = itemsList.items.find((i: any) => i.question_id === it.id);
          return {
            id: it.id,
            label: it.label,
            status: item?.has_images ? "done" as CropStatus : "pending" as CropStatus,
            itemId: item?.item_id,
            imageUrls: item?.image_urls || [],
          };
        });
        setQuestions(mapped);
        setSelectedQuestionId(mapped.find(q => q.status === "pending")?.id ?? mapped[0]?.id ?? null);
        // Seed graded set initially
        try { await checkGradingStatus(); } catch {}
      } catch (e: any) {
        toast.error(e?.message || "Failed to load submission data");
      } finally {
        setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, [submissionId]);

  // In-panel tabs removed: tabs now live under the sidebar automatically

  const handleCropSave = async (cropData: {
    answer_bbox_coordinates: { left: number; top: number; width: number; height: number };
    original_image_dimensions: { width: number; height: number };
  }) => {
    if (!submissionId || selectedQuestionId == null || saving) return;

    const { left, top, width, height } = cropData.answer_bbox_coordinates;
    const { width: origW, height: origH } = cropData.original_image_dimensions;
    const bbox = { x: left / origW, y: top / origH, w: width / origW, h: height / origH, normalized: true as const };

    try {
      setSaving(true);
      const itemsList = await getSubmissionItemsList(submissionId);
      const existing = itemsList.items.find((i: any) => i.question_id === selectedQuestionId);
      if (!existing) {
        // First image for this question -> create item
        await createSubmissionItem(submissionId, { question_id: selectedQuestionId, page_index: pageIndex, bbox });
      } else {
        // Item exists -> append another answer image
        await appendSubmissionItemImage(existing.item_id, { page_index: pageIndex, bbox });
      }
      toast.success("Answer crop saved. Click Grade to start grading.");
      // Refresh items list after save/append
      const itemsList2 = await getSubmissionItemsList(submissionId);
      setQuestions((prev) => prev.map((q) => {
        const item = itemsList2.items.find((i: any) => i.question_id === q.id);
        return item?.has_images ? { ...q, status: "done" as CropStatus, itemId: item.item_id, imageUrls: item.image_urls } : q;
      }));
    } catch (e: any) {
      toast.error(e?.message || "Failed to save answer crop");
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteItem = async (itemId: number) => {
    if (!confirm("Delete this answer crop? This cannot be undone.")) {
      return;
    }
    
    try {
      await deleteSubmissionItem(itemId);
      toast.success("Item deleted");
      // Update local state
      setQuestions((prev) => prev.map((q) => 
        q.itemId === itemId ? { ...q, status: "pending" as CropStatus, itemId: undefined, imageUrls: [] } : q
      ));
    } catch (e: any) {
      toast.error(e?.message || "Failed to delete item");
    }
  };

  if (!submissionId || isNaN(submissionId) || submissionId <= 0) {
    return (
      <div className="flex h-[calc(100vh-4rem)] items-center justify-center">
        <div className="text-center">
          <h2 className="text-xl font-bold text-foreground mb-2">Invalid Submission</h2>
          <p className="text-muted-foreground mb-4">No valid submission ID provided in the URL.</p>
          <Button onClick={() => navigate("/submissions")}>
            Back to Submissions
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-4rem)] gap-0">
      {/* Left Pane - Question List (30%) */}
      <div className="w-[30%] border-r border-border overflow-y-auto bg-background p-6 space-y-6">
        <div>
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-xl font-bold text-foreground">Student: {studentName || "—"}</h2>
            {connected && (
              <Badge variant="outline" className="text-xs gap-1">
                <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
                Live
              </Badge>
            )}
          </div>
          <p className="text-sm text-muted-foreground">Select question to crop answer</p>
        </div>

        {/* In-panel tabs removed for simplicity */}

        <div className="space-y-2">
          {loading && <div className="text-xs text-muted-foreground">Loading…</div>}
          {questions.map((question) => (
            <Card
              key={question.id}
              className={`p-4 transition-all ${
                selectedQuestionId === question.id ? "ring-2 ring-primary" : ""
              } ${
                gradedQuestionIds.has(question.id)
                  ? "bg-green-50 border-green-300"
                  : "bg-yellow-50 border-yellow-300"
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <div 
                  className="flex items-center gap-2 flex-1 cursor-pointer"
                  onClick={() => setSelectedQuestionId(question.id)}
                >
                  <span className="font-medium text-foreground">{question.label}</span>
                  {gradedQuestionIds.has(question.id) && <CheckCircle className="h-5 w-5 text-green-600" />}
                  {question.status === "grading" && <Loader2 className="h-5 w-5 animate-spin text-primary" />}
                </div>
                <div className="flex items-center gap-2">
                  {question.itemId && (
                    <>
                      <Button
                        size="sm"
                        variant={question.status === "grading" ? "secondary" : "default"}
                        disabled={question.status === "grading"}
                        onClick={async (e) => {
                          e.stopPropagation();
                          try {
                            setQuestions((prev) => prev.map((q) => q.id === question.id ? { ...q, status: "grading" as CropStatus } : q));
                            setGradingStartByQuestionId((prev) => ({ ...prev, [question.id]: Date.now() }));
                            await gradeItem(question.itemId!);
                            toast.success("Grading started for this answer");
                            // polling will flip to done or WS handler will refresh
                          } catch (err: any) {
                            toast.error(err?.message || "Failed to start grading");
                            setQuestions((prev) => prev.map((q) => q.id === question.id ? { ...q, status: "done" as CropStatus } : q));
                          }
                        }}
                      >
                        {question.status === "grading" ? <><Loader2 className="h-3 w-3 animate-spin mr-1"/>Grading…</> : "Grade"}
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-6 w-6 p-0 text-destructive hover:text-destructive hover:bg-destructive/10"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteItem(question.itemId!);
                        }}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </>
                  )}
                </div>
              </div>
              {/* Status badges */}
              {question.itemId && question.status !== "grading" && !gradedQuestionIds.has(question.id) && (
                <Badge variant="secondary" className="gap-1 bg-yellow-100 text-yellow-800 border-yellow-200">
                  🕒 Waiting for grading
                </Badge>
              )}
              {question.status === "grading" && (
                <Badge variant="secondary" className="gap-1 bg-yellow-100 text-yellow-800 border-yellow-200">
                  <span className="mr-1">⏳</span>
                  Grading...
                  <span className="ml-1">
                    {(() => {
                      const start = gradingStartByQuestionId[question.id];
                      const ms = start ? Math.max(0, Date.now() - start + tick * 0) : 0;
                      const s = Math.floor(ms / 1000);
                      const m = Math.floor(s / 60);
                      const sec = s % 60;
                      return `${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
                    })()}
                  </span>
                </Badge>
              )}
              {gradedQuestionIds.has(question.id) && (
                <Badge variant="default" className="gap-1 bg-green-600">
                  <CheckCircle className="h-3 w-3" />
                  Graded
                </Badge>
              )}
              {gradedQuestionIds.has(question.id) && question.imageUrls && question.imageUrls.length > 0 && (
                <div className="mt-2 space-y-2">
                  <Badge variant="default" className="gap-1 bg-green-600">
                    <CheckCircle className="h-3 w-3" />
                    Cropped ({question.imageUrls.length})
                  </Badge>
                  <div className="flex gap-2 flex-wrap">
                    {question.imageUrls.map((url, idx) => (
                      <div 
                        key={idx} 
                        className="w-16 h-16 border border-border rounded overflow-hidden cursor-pointer hover:ring-2 hover:ring-primary"
                        onClick={() => setPreviewImageUrl(url)}
                      >
                        <img 
                          src={url} 
                          alt={`Answer ${idx + 1}`}
                          className="w-full h-full object-contain bg-white"
                        />
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </Card>
          ))}
        </div>

        <div className="flex gap-2">
          <Button className="flex-1" onClick={() => navigate(`/grading?submissionId=${submissionId}`)} size="lg">
            View All Results
          </Button>
          <Button
            variant="secondary"
            onClick={async () => {
              try {
                // Set all with items to grading
                setQuestions((prev) => prev.map((q) => q.itemId ? { ...q, status: "grading" as CropStatus } : q));
                setGradingStartByQuestionId((prev) => {
                  const next = { ...prev } as Record<number, number>;
                  questions.forEach((q) => { if (q.itemId) next[q.id] = Date.now(); });
                  return next;
                });
                await gradeSubmission(submissionId);
                toast.success("Grading started for all answers");
              } catch (e: any) {
                toast.error(e?.message || "Failed to grade all");
              }
            }}
            size="lg"
          >
            Grade All
          </Button>
        </div>
      </div>

      {/* Right Pane - Cropping Canvas (70%) */}
      <div className="w-[70%] overflow-y-auto bg-muted/10 p-8">
        <div className="mb-4">
          <h2 className="text-xl font-bold text-foreground">
            Crop Answer: {selectedQuestionId != null ? questions.find(q => q.id === selectedQuestionId)?.label : "Select a question"}
          </h2>
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">Draw a rectangle around the student's answer</p>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={() => setPageIndex((p) => Math.max(0, p - 1))} disabled={pageIndex <= 0}>
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <span className="text-sm text-muted-foreground">Page {images.length ? pageIndex + 1 : 0} / {images.length}</span>
              <Button variant="outline" size="sm" onClick={() => setPageIndex((p) => Math.min(images.length - 1, p + 1))} disabled={pageIndex >= images.length - 1}>
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
        {selectedQuestionId != null && currentImage && (
          <CroppingCanvas
            imageUrl={currentImage}
            onCropSave={handleCropSave}
            saving={saving}
          />
        )}
        {selectedQuestionId != null && !currentImage && (
          <Card className="p-6"><p className="text-sm text-muted-foreground">No pages available for this submission.</p></Card>
        )}
      </div>
      
      {/* Image Preview Modal */}
      {previewImageUrl && (
        <div 
          className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-4"
          onClick={() => setPreviewImageUrl(null)}
        >
          <div className="relative max-w-4xl max-h-[90vh]">
            <Button
              size="sm"
              variant="ghost"
              className="absolute -top-10 right-0 text-white hover:text-white hover:bg-white/20"
              onClick={() => setPreviewImageUrl(null)}
            >
              Close
            </Button>
            <img 
              src={previewImageUrl} 
              alt="Preview"
              className="max-w-full max-h-[90vh] object-contain"
              onClick={(e) => e.stopPropagation()}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default CropSubmission;
