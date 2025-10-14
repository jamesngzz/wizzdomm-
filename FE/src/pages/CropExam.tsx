import { useEffect, useMemo, useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Crop, FileText, CheckCircle, Loader2, ChevronLeft, ChevronRight, ArrowLeft, ChevronDown, ChevronRight as ChevronRightIcon, Trash2, X } from "lucide-react";
import { CroppingCanvas } from "@/components/CroppingCanvas";
import { toast } from "sonner";
import { Link, useSearchParams } from "react-router-dom";
import { createQuestion, getExamImages, listExamQuestions, solveQuestion, getQuestionSolution, verifyQuestionSolution, getQuestionImages, appendQuestionImage, deleteQuestion, deleteQuestionImage } from "@/lib/api";

type QuestionStatus = "waiting" | "solving" | "ready";

const CropExam = () => {
  const [sp] = useSearchParams();
  const examId = Number(sp.get("examId"));

  const [questionLabel, setQuestionLabel] = useState("");
  const [selectedQuestionId, setSelectedQuestionId] = useState<number | null>(null); // For appending to existing question
  const [images, setImages] = useState<string[]>([]);
  const [pageIndex, setPageIndex] = useState(0);
  const [loadingImages, setLoadingImages] = useState(false);
  const [questions, setQuestions] = useState<Array<{ id: number; label: string; status: QuestionStatus }>>([]);
  const [loadingQuestions, setLoadingQuestions] = useState(false);
  const [solutionByQuestionId, setSolutionByQuestionId] = useState<Record<number, { answer?: string; steps?: any[]; points?: number[]; generated_at?: string; verified?: boolean }>>({});
  const [busyQuestionId, setBusyQuestionId] = useState<number | null>(null);
  const [expandedQuestions, setExpandedQuestions] = useState<Set<number>>(new Set());
  const [questionImages, setQuestionImages] = useState<Record<number, string[]>>({});
  const [viewModes, setViewModes] = useState<Record<number, 'images' | 'solution'>>({});

  const currentImage = useMemo(() => images[pageIndex] || "", [images, pageIndex]);

  useEffect(() => {
    if (!examId) return;
    let mounted = true;
    setLoadingImages(true);
    getExamImages(examId)
      .then((res) => {
        if (!mounted) return;
        setImages(res.urls || []);
        setPageIndex(0);
      })
      .catch((e) => toast.error(e?.message || "Failed to load exam images"))
      .finally(() => setLoadingImages(false));
    return () => {
      mounted = false;
    };
  }, [examId]);

  useEffect(() => {
    if (!examId) return;
    let mounted = true;
    setLoadingQuestions(true);
    listExamQuestions(examId)
      .then(async (res) => {
        if (!mounted) return;
        // Load solution status for each question to determine initial status
        const mapped = (res.items || []).map((it: any) => ({ id: it.id, label: it.label, status: "waiting" as QuestionStatus }));
        setQuestions(mapped);
        
        // Fetch solution data for all questions to set proper status
        for (const q of mapped) {
          try {
            const sol = await getQuestionSolution(q.id);
            if (!mounted) return;
            if (sol?.generated_at) {
              setQuestions(prev => prev.map(item => 
                item.id === q.id ? { ...item, status: "ready" as QuestionStatus } : item
              ));
              setSolutionByQuestionId(prev => ({
                ...prev,
                [q.id]: {
                  answer: sol.answer,
                  steps: sol.steps,
                  points: sol.points,
                  generated_at: sol.generated_at,
                  verified: sol.verified,
                }
              }));
            }
          } catch (e) {
            // Question doesn't have solution yet, keep as "waiting"
          }
        }
      })
      .catch((e) => toast.error(e?.message || "Failed to load questions"))
      .finally(() => setLoadingQuestions(false));
    return () => {
      mounted = false;
    };
  }, [examId]);

  const handleCropSave = async (cropData: {
    answer_bbox_coordinates: { left: number; top: number; width: number; height: number };
    original_image_dimensions: { width: number; height: number };
  }) => {
    if (!examId) {
      toast.error("Missing examId");
      return;
    }
    if (!currentImage) {
      toast.error("No image selected");
      return;
    }

    const { left, top, width, height } = cropData.answer_bbox_coordinates;
    const { width: origW, height: origH } = cropData.original_image_dimensions;
    const normalized = {
      x: left / origW,
      y: top / origH,
      w: width / origW,
      h: height / origH,
      normalized: true as const,
    };

    try {
      // Check if we're appending to an existing question
      if (selectedQuestionId) {
        await appendQuestionImage(selectedQuestionId, { page_index: pageIndex, bbox: normalized });
        toast.success(`Added image to question`);
        // Refresh images for this question
        const res = await getQuestionImages(selectedQuestionId);
        setQuestionImages(prev => ({ ...prev, [selectedQuestionId]: res.urls }));
      } else {
        // Creating a new question
        if (!questionLabel) {
          toast.error("Please enter a question label");
          return;
        }
        await createQuestion({ exam: examId, label: questionLabel, page_index: pageIndex, bbox: normalized });
        toast.success(`Saved question "${questionLabel}"`);
        setQuestionLabel("");
        // Refresh list
        const res = await listExamQuestions(examId);
        const mapped = (res.items || []).map((it: any) => ({ id: it.id, label: it.label, status: "waiting" as QuestionStatus }));
        // Update status for questions that already have solutions
        for (const q of mapped) {
          if (solutionByQuestionId[q.id]?.generated_at) {
            q.status = "ready";
          }
        }
        setQuestions(mapped);
      }
    } catch (e: any) {
      toast.error(e?.message || "Save question failed");
    }
  };

  const handleSolve = async (questionId: number) => {
    try {
      setBusyQuestionId(questionId);
      // Set status to "solving"
      setQuestions(prev => prev.map(q => q.id === questionId ? { ...q, status: "solving" as QuestionStatus } : q));
      
      await solveQuestion(questionId);
      const sol = await getQuestionSolution(questionId);
      
      // Set status to "ready" after solution is generated
      setQuestions(prev => prev.map(q => q.id === questionId ? { ...q, status: "ready" as QuestionStatus } : q));
      
      setSolutionByQuestionId((prev) => ({
        ...prev,
        [questionId]: {
          answer: sol?.answer,
          steps: sol?.steps,
          points: sol?.points,
          generated_at: sol?.generated_at,
          verified: !!sol?.verified,
        },
      }));
      toast.success("Solution generated");
    } catch (e: any) {
      // Revert to "waiting" on error
      setQuestions(prev => prev.map(q => q.id === questionId ? { ...q, status: "waiting" as QuestionStatus } : q));
      toast.error(e?.message || "Solve failed");
    } finally {
      setBusyQuestionId(null);
    }
  };

  // Removed explicit View Solution handler; solutions are visible when expanding a question

  const handleVerify = async (questionId: number, verified: boolean) => {
    try {
      setBusyQuestionId(questionId);
      await verifyQuestionSolution(questionId, verified);
      setSolutionByQuestionId((prev) => ({
        ...prev,
        [questionId]: { ...(prev[questionId] || {}), verified },
      }));
      toast.success(verified ? "Marked verified" : "Marked unverified");
    } catch (e: any) {
      toast.error(e?.message || "Verify failed");
    } finally {
      setBusyQuestionId(null);
    }
  };

  const handleToggleQuestionExpand = async (questionId: number) => {
    const isExpanded = expandedQuestions.has(questionId);
    const newExpanded = new Set(expandedQuestions);
    
    if (isExpanded) {
      newExpanded.delete(questionId);
    } else {
      newExpanded.add(questionId);
      // Set default view mode to images
      if (!viewModes[questionId]) {
        setViewModes(prev => ({ ...prev, [questionId]: 'images' }));
      }
      // Fetch images if not already loaded
      if (!questionImages[questionId]) {
        try {
          const res = await getQuestionImages(questionId);
          setQuestionImages(prev => ({ ...prev, [questionId]: res.urls }));
        } catch (e: any) {
          toast.error(e?.message || "Failed to load images");
        }
      }
    }
    
    setExpandedQuestions(newExpanded);
  };

  const handleDeleteQuestion = async (questionId: number) => {
    const question = questions.find(q => q.id === questionId);
    if (!confirm(`Delete question "${question?.label}"? This cannot be undone.`)) {
      return;
    }
    
    try {
      await deleteQuestion(questionId);
      toast.success("Question deleted");
      // Remove from local state
      setQuestions(prev => prev.filter(q => q.id !== questionId));
      setSolutionByQuestionId(prev => {
        const newObj = { ...prev };
        delete newObj[questionId];
        return newObj;
      });
      setQuestionImages(prev => {
        const newObj = { ...prev };
        delete newObj[questionId];
        return newObj;
      });
      expandedQuestions.delete(questionId);
      setExpandedQuestions(new Set(expandedQuestions));
    } catch (e: any) {
      toast.error(e?.message || "Failed to delete question");
    }
  };

  const handleDeleteQuestionImage = async (questionId: number, imageIndex: number) => {
    if (!confirm(`Delete this image? This cannot be undone.`)) {
      return;
    }
    
    try {
      await deleteQuestionImage(questionId, imageIndex);
      toast.success("Image deleted");
      // Refresh images for this question
      const res = await getQuestionImages(questionId);
      setQuestionImages(prev => ({ ...prev, [questionId]: res.urls }));
    } catch (e: any) {
      toast.error(e?.message || "Failed to delete image");
    }
  };

  const getStatusBadge = (status: QuestionStatus) => {
    if (status === "ready") {
      return (
        <Badge variant="default" className="gap-1 bg-green-600">
          <CheckCircle className="h-3 w-3" />
          Solution Ready
        </Badge>
      );
    }
    if (status === "solving") {
      return (
        <Badge variant="secondary" className="gap-1 bg-blue-500 text-white">
          <Loader2 className="h-3 w-3 animate-spin" />
          Solving...
        </Badge>
      );
    }
    if (status === "waiting") {
      return (
        <Badge variant="outline" className="gap-1 bg-yellow-100 text-yellow-800 border-yellow-300">
          <FileText className="h-3 w-3" />
          Wait for solving
        </Badge>
      );
    }
    return null;
  };

  return (
    <div className="flex h-[calc(100vh-4rem)] gap-0">
      {/* Right Pane - Control Panel (30%) */}
      <div className="w-[30%] border-r border-border overflow-y-auto bg-background p-6 space-y-6">
        <div>
          <Button variant="ghost" size="sm" asChild className="mb-4 gap-2">
            <Link to="/exams">
              <ArrowLeft className="h-4 w-4" />
              Back to Exam List
            </Link>
          </Button>
          <h2 className="text-xl font-bold text-foreground mb-2">Questions</h2>
          <p className="text-sm text-muted-foreground">Crop and generate solutions</p>
        </div>

        <div className="space-y-3">
          {loadingQuestions && <p className="text-xs text-muted-foreground">Loading…</p>}
          {questions.map((question) => {
            const sol = solutionByQuestionId[question.id];
            const isBusy = busyQuestionId === question.id;
            const isExpanded = expandedQuestions.has(question.id);
            const images = questionImages[question.id] || [];
            return (
              <Card key={question.id} className="p-4 space-y-2">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2 cursor-pointer" onClick={() => handleToggleQuestionExpand(question.id)}>
                    {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRightIcon className="h-4 w-4" />}
                    <span className="font-medium text-foreground">{question.label}</span>
                    {images.length > 0 && <Badge variant="secondary" className="text-xs">{images.length} img</Badge>}
                  </div>
                  <div className="flex items-center gap-2">
                    {getStatusBadge(question.status)}
                    <Button 
                      size="sm" 
                      variant="ghost" 
                      className="h-6 w-6 p-0 text-destructive hover:text-destructive hover:bg-destructive/10"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteQuestion(question.id);
                      }}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" onClick={() => handleSolve(question.id)} disabled={isBusy}>
                    {isBusy ? "Solving…" : "Solve"}
                  </Button>
                  <Button 
                    size="sm" 
                    className={sol?.verified ? "bg-green-600 hover:bg-green-700 text-white" : "bg-yellow-400 hover:bg-yellow-500 text-black"}
                    onClick={() => handleVerify(question.id, !sol?.verified)} 
                    disabled={isBusy}
                  >
                    {sol?.verified ? "✓ Verified" : "Verify"}
                  </Button>
                </div>
                
                {/* View mode tabs and content */}
                {isExpanded && (images.length > 0 || sol) && (
                  <div className="mt-2 pt-2 border-t border-border">
                    {/* Tabs */}
                    <div className="flex gap-2 mb-3">
                      <Button 
                        size="sm" 
                        variant={viewModes[question.id] === 'images' ? 'default' : 'outline'}
                        onClick={() => setViewModes(prev => ({ ...prev, [question.id]: 'images' }))}
                        className="gap-1"
                      >
                        📸 Images ({images.length})
                      </Button>
                      <Button 
                        size="sm" 
                        variant={viewModes[question.id] === 'solution' ? 'default' : 'outline'}
                        onClick={() => setViewModes(prev => ({ ...prev, [question.id]: 'solution' }))}
                        className="gap-1"
                        disabled={!sol}
                      >
                        📝 Solution
                      </Button>
                    </div>
                    
                    {/* Images View */}
                    {viewModes[question.id] === 'images' && images.length > 0 && (
                      <div className="grid grid-cols-2 gap-2">
                        {images.map((imgUrl, idx) => (
                          <div key={idx} className="relative border border-border rounded overflow-hidden group">
                            <img 
                              src={imgUrl} 
                              alt={`Question ${question.label} - ${idx + 1}`}
                              className="w-full h-20 object-contain bg-muted cursor-pointer"
                              onClick={() => window.open(imgUrl, '_blank')}
                            />
                            <button
                              className="absolute top-1 right-1 bg-destructive text-destructive-foreground rounded-full p-1 opacity-0 group-hover:opacity-100 transition-opacity"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleDeleteQuestionImage(question.id, idx);
                              }}
                            >
                              <X className="h-3 w-3" />
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                    
                    {/* Solution View */}
                    {viewModes[question.id] === 'solution' && sol && (
                      <div className="text-xs space-y-1">
                        <p className="text-muted-foreground">Verified: {sol.verified ? "Yes" : "No"}</p>
                        {sol.answer && (
                          <p><span className="font-medium">Answer:</span> {sol.answer}</p>
                        )}
                        {Array.isArray(sol.steps) && sol.steps.length > 0 && (
                          <div className="space-y-1">
                            <p className="font-medium">Steps:</p>
                            <ul className="list-disc ml-4">
                              {sol.steps.map((s, i) => (
                                <li key={i} className="text-foreground/90 break-words">
                                  <div className="font-medium">Bước {(s as any)?.step_number || i + 1}:</div>
                                  <div className="text-sm">{(s as any)?.description || ''}</div>
                                  <div className="text-xs text-muted-foreground mt-1">{(s as any)?.content || ''}</div>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </Card>
            );
          })}
        </div>

      </div>

      {/* Left Pane - Canvas (70%) */}
      <div className="w-[70%] overflow-y-auto bg-muted/10 p-8">
        <div className="mb-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-bold text-foreground">Exam Paper</h2>
              <p className="text-sm text-muted-foreground">Draw rectangles to crop questions</p>
            </div>
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
        {loadingImages && <p className="text-sm text-muted-foreground">Loading pages…</p>}
        {!loadingImages && currentImage && (
          <div className="space-y-4">
            <div className="flex gap-3 items-start">
              <div className="space-y-2">
                <label className="text-sm font-medium">Mode:</label>
                <Select 
                  value={selectedQuestionId ? String(selectedQuestionId) : "new"} 
                  onValueChange={(val) => setSelectedQuestionId(val === "new" ? null : Number(val))}
                >
                  <SelectTrigger className="w-48">
                    <SelectValue placeholder="Create new or append" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="new">Create New Question</SelectItem>
                    {questions.map(q => (
                      <SelectItem key={q.id} value={String(q.id)}>Add to {q.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              {!selectedQuestionId && (
                <div className="space-y-2">
                  <label className="text-sm font-medium">Question Label:</label>
                  <Input
                    placeholder="e.g., Bài 2a"
                    value={questionLabel}
                    onChange={(e) => setQuestionLabel(e.target.value)}
                    className="w-48"
                  />
                </div>
              )}
              
              {selectedQuestionId && (
                <div className="space-y-2">
                  <label className="text-sm font-medium">Target:</label>
                  <div className="text-sm text-muted-foreground p-2 border rounded bg-muted">
                    Appending to: {questions.find(q => q.id === selectedQuestionId)?.label}
                  </div>
                </div>
              )}
            </div>
            <CroppingCanvas
              imageUrl={currentImage}
              onCropSave={handleCropSave}
            />
          </div>
        )}
        {!loadingImages && !currentImage && (
          <Card className="p-6">
            <p className="text-sm text-muted-foreground">No pages available. Upload exam files first.</p>
          </Card>
        )}
      </div>
    </div>
  );
};

export default CropExam;
