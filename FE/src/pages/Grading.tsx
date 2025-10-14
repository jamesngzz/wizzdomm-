import { useState, useEffect, useRef, useCallback } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { AlertCircle, RefreshCw, Download, ChevronDown, ChevronRight, Loader2, CheckCircle } from "lucide-react";
import { toast } from "sonner";
import { useSearchParams, useNavigate } from "react-router-dom";
import { gradingSummary, regradeSubmission, exportSubmission, getQuestionSolution } from "@/lib/api";
import { ItemAnnotationCanvas } from "@/components/ItemAnnotationCanvas";
import { useWebSocket } from "@/hooks/use-websocket";

interface SummaryItem {
  item_id: number;
  question: { id: number; label: string };
  graded: boolean;
  is_correct: boolean | null;
  critical_errors?: any;
  part_errors?: any;
  partial_credit?: any;
}

const Grading = () => {
  const navigate = useNavigate();
  const [sp] = useSearchParams();
  const submissionId = Number(sp.get("submissionId"));
  const [clarificationText, setClarificationText] = useState("");
  // Active item and visible page index (within that item)
  const [activeItemId, setActiveItemId] = useState<number | null>(null);
  const [activePageIndexByItem, setActivePageIndexByItem] = useState<Record<number, number>>({});
  const [solutionOpen, setSolutionOpen] = useState(false);
  const [activeSolution, setActiveSolution] = useState<{ answer: string; steps: unknown[]; points: number[] } | null>(null);
  const [summary, setSummary] = useState<{ submission: number; student_name: string; items: SummaryItem[] } | null>(null);
  const [loading, setLoading] = useState(false);
  const [regrading, setRegrading] = useState(false);
  const [regradeStartAt, setRegradeStartAt] = useState<number | null>(null);
  const [recentlyRegraded, setRecentlyRegraded] = useState(false);
  const [tick, setTick] = useState(0);

  const currentItems: SummaryItem[] = (summary?.items || []);
  const gradedItems = currentItems.filter((i) => i.graded);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const itemRefs = useRef<Record<number, HTMLDivElement | null>>({});

  useEffect(() => {
    if (!submissionId) return;
    let mounted = true;
    (async () => {
      try {
        setLoading(true);
        const sum = await gradingSummary(submissionId);
        if (!mounted) return;
        setSummary(sum as any);
        // Set first graded item as active
        const first = (sum.items || []).find((it: any) => it.graded) || (sum.items || [])[0];
        if (first) setActiveItemId(first.item_id);
      } catch (e: any) {
        toast.error(e?.message || "Failed to load grading data");
      } finally {
        setLoading(false);
      }
    })();
    return () => { mounted = false; };
  }, [submissionId]);

  // Detect active item by scroll position
  const computeActiveItem = useCallback(() => {
    const root = containerRef.current;
    if (!root) return;
    const center = root.scrollTop + root.clientHeight / 2;
    let bestId: number | null = null;
    let bestDist = Infinity;
    for (const item of gradedItems) {
      const el = itemRefs.current[item.item_id];
      if (!el) continue;
      const top = el.offsetTop;
      const height = el.offsetHeight;
      const mid = top + height / 2;
      const dist = Math.abs(mid - center);
      if (dist < bestDist) {
        bestDist = dist;
        bestId = item.item_id;
      }
    }
    if (bestId && bestId !== activeItemId) {
      setActiveItemId(bestId);
      setSolutionOpen(false);
    }
  }, [gradedItems, activeItemId]);

  useEffect(() => {
    const root = containerRef.current;
    if (!root) return;
    const handler = () => computeActiveItem();
    handler();
    root.addEventListener("scroll", handler, { passive: true });
    return () => root.removeEventListener("scroll", handler as any);
  }, [computeActiveItem]);

  // Timer tick while regrading to update duration label
  useEffect(() => {
    if (!regrading) return;
    const id = setInterval(() => setTick((t) => t + 1), 1000);
    return () => clearInterval(id);
  }, [regrading]);

  // WebSocket: detect submission (re)grade completion
  useWebSocket((msg) => {
    if (
      (msg.event === "GRADE_SUBMISSION" || msg.event === "RE_GRADE_SUBMISSION" || msg.event === "REGRADE_SUBMISSION") &&
      msg.status === "succeeded"
    ) {
      setRegrading(false);
      setRegradeStartAt(null);
      setRecentlyRegraded(true);
      setTimeout(() => setRecentlyRegraded(false), 6000);
      gradingSummary(submissionId).then((sum) => setSummary(sum as any)).catch(() => {});
    }
  });


  // Load active solution on active item change
  useEffect(() => {
    const load = async () => {
      try {
        const it = (currentItems || []).find((x) => x.item_id === activeItemId);
        if (!it?.question?.id) { setActiveSolution(null); return; }
        const sol = await getQuestionSolution(it.question.id);
        setActiveSolution({ answer: sol.answer, steps: (sol.steps || []) as unknown[], points: (sol.points || []) as number[] });

        // Dispatch an event to update sidebar tab label with student name and Q label
        try {
          const label = `${summary?.student_name || ''} • Q${it.question.label}`.trim();
          window.dispatchEvent(new CustomEvent("ta:update-grading-tab", { detail: { id: Number(sp.get("submissionId")), label } }));
        } catch {}
      } catch {
        setActiveSolution(null);
      }
    };
    if (activeItemId) load();
  }, [activeItemId, currentItems]);

  // No in-panel tabs; tabs are handled in sidebar menu

  const handleRegrade = async () => {
    if (!submissionId || !clarificationText) {
      toast.error("Please enter clarification notes");
      return;
    }

    try {
      setRegrading(true);
      setRegradeStartAt(Date.now());
      await regradeSubmission(submissionId, clarificationText);
      toast.success("Regrade requested! Regrading is in progress.");
      setClarificationText("");
      // Optional immediate refresh; further updates handled by WS
      try {
        const sum = await gradingSummary(submissionId);
        setSummary(sum as any);
      } catch {}
    } catch (e: any) {
      toast.error(e?.message || "Regrade failed");
      setRegrading(false);
    }
  };

  const handleExport = async () => {
    if (!submissionId) return;
    try {
      const res = await exportSubmission(submissionId);
      let url = res.pdf_url;
      if (url) {
        // URL is already correct (relative or absolute)
        // Vite proxy will forward /media requests to Django backend
        window.open(url, "_blank");
      }
    } catch (e: any) {
      toast.error(e?.message || "Export failed");
    }
  };

  const handleAnnotationsSaved = async () => {
    // Optionally reload summary after saving annotations
    try {
      const sum = await gradingSummary(submissionId);
      setSummary(sum as any);
    } catch (e: any) {
      console.error("Failed to reload summary:", e);
    }
  };

  const selectedItem = currentItems.find(item => item.item_id === activeItemId);

  // Show error if no submissionId provided
  if (!submissionId || isNaN(submissionId) || submissionId <= 0) {
    return (
      <div className="flex h-[calc(100vh-4rem)] items-center justify-center">
        <div className="text-center">
          <h2 className="text-xl font-bold text-foreground mb-2">No Submission Selected</h2>
          <p className="text-muted-foreground mb-4">Please select a submission to view grading results.</p>
          <Button onClick={() => navigate("/submissions")}>
            Back to Submissions
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-4rem)] gap-0">
      {/* Left Pane - All graded items stacked */}
      <div className="w-[65%] border-r border-border overflow-hidden flex flex-col">
        <div className="px-3 py-2 border-b border-border bg-background">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-base font-semibold text-foreground">
              {summary?.student_name || "Student"}
            </h2>
            <div className="text-xs text-muted-foreground">{gradedItems.length} graded question(s)</div>
          </div>
        </div>
        <div ref={containerRef} className="flex-1 overflow-y-auto p-2 space-y-4">
          {gradedItems.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center space-y-2">
                <AlertCircle className="h-12 w-12 mx-auto text-muted-foreground" />
                <p className="text-muted-foreground">No graded items yet</p>
              </div>
            </div>
          ) : (
            gradedItems.map((it) => (
              <div
                key={it.item_id}
                ref={(el) => { itemRefs.current[it.item_id] = el; }}
                className={`rounded-lg border ${activeItemId === it.item_id ? "border-primary" : "border-border"}`}
              >
                <div className="flex items-center justify-between px-3 py-2 border-b">
                  <div className="font-medium text-sm">Question {it.question.label}</div>
                  <Badge variant={it.is_correct ? "default" : "destructive"}>
                    {it.is_correct == null ? "Pending" : it.is_correct ? "Correct" : "Incorrect"}
                  </Badge>
                </div>
                <div className="p-2">
                  <ItemAnnotationCanvas
                    itemId={it.item_id}
                    onSaved={handleAnnotationsSaved}
                    onVisiblePageChange={(idx) => setActivePageIndexByItem((prev) => ({ ...prev, [it.item_id]: idx }))}
                  />
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Right Pane - Dynamic details (35%) */}
      <div className="w-[35%] overflow-y-auto bg-background">
        <div className="p-2 space-y-3">
          {/* Regrade status header */}
          {!regrading && !recentlyRegraded && (
            <Card className="p-2 border border-yellow-300 bg-yellow-50">
              <div className="flex items-center justify-between">
                <div className="text-xs text-yellow-800">🕒 Waiting for regrade</div>
              </div>
            </Card>
          )}
          {regrading && (
            <Card className="p-2 border border-yellow-300 bg-yellow-50">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-yellow-800">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Regrading…</span>
                </div>
                <div className="text-xs text-yellow-800">
                  {(() => {
                    const start = regradeStartAt || Date.now();
                    const total = Math.max(0, Date.now() - start);
                    const s = Math.floor(total / 1000);
                    const m = Math.floor(s / 60);
                    const sec = s % 60;
                    return `${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
                  })()}
                </div>
              </div>
            </Card>
          )}
          {!regrading && recentlyRegraded && (
            <Card className="p-2 border border-green-300 bg-green-50">
              <div className="flex items-center gap-2 text-green-700">
                <CheckCircle className="h-4 w-4" />
                <span>Regraded</span>
              </div>
            </Card>
          )}
          {selectedItem && (
            <Card className="p-3 space-y-2 border border-primary/50">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <h3 className="font-semibold text-base">Question {selectedItem.question.label}</h3>
                  <p className="text-xs text-muted-foreground">
                    Page {(activePageIndexByItem[activeItemId || -1] ?? 0) + 1}
                  </p>
                </div>
                <Badge variant={selectedItem.is_correct ? "default" : "destructive"}>
                  {selectedItem.is_correct == null ? "Pending" : selectedItem.is_correct ? "Correct" : "Incorrect"}
                </Badge>
              </div>

              {/* Toggle for solution/explanation */}
              <button
                className="w-full text-left flex items-center justify-between px-2 py-2 rounded hover:bg-muted"
                onClick={() => setSolutionOpen((v) => !v)}
              >
                <span className="text-sm font-medium">Lời giải bài làm</span>
                {solutionOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
              </button>
              {solutionOpen && (
                <div className="space-y-2 rounded border p-2">
                  {activeSolution ? (
                    <div className="space-y-2">
                      {activeSolution.answer && (
                        <p className="text-sm whitespace-pre-wrap">{activeSolution.answer}</p>
                      )}
                      {Array.isArray(activeSolution.steps) && activeSolution.steps.length > 0 && (
                        <div>
                          <p className="text-xs font-semibold mb-1">Các bước:</p>
                          <ul className="list-disc pl-5 space-y-1">
                            {(activeSolution.steps as any[]).slice(0, 20).map((s, i) => (
                              <li key={i} className="text-sm">
                                {typeof s === 'string' ? s : JSON.stringify(s)}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">Không có lời giải khả dụng.</p>
                  )}
                </div>
              )}

              {/* Errors summary collapsed by default */}
              {(Array.isArray(selectedItem.critical_errors) && selectedItem.critical_errors.length > 0) && (
                <div className="space-y-1">
                  <h4 className="text-xs font-semibold text-destructive uppercase">Critical</h4>
                  {selectedItem.critical_errors.slice(0, 5).map((error: any, idx: number) => (
                    <div key={idx} className="p-2 bg-destructive/10 rounded border border-destructive/20 text-xs">
                      {error?.description || String(error)}
                    </div>
                  ))}
                </div>
              )}
              {(Array.isArray(selectedItem.part_errors) && selectedItem.part_errors.length > 0) && (
                <div className="space-y-1">
                  <h4 className="text-xs font-semibold text-warning uppercase">Partial</h4>
                  {selectedItem.part_errors.slice(0, 5).map((error: any, idx: number) => (
                    <div key={idx} className="p-2 bg-warning/10 rounded border border-warning/20 text-xs">
                      {error?.description || error?.message || String(error)}
                    </div>
                  ))}
                </div>
              )}

              {/* Regrade Section */}
              <div className="pt-2 border-t border-border space-y-2">
                <label className="text-xs font-medium text-muted-foreground">Teacher Clarification</label>
                <Textarea
                  placeholder="Add notes for AI to reconsider..."
                  value={clarificationText}
                  onChange={(e) => setClarificationText(e.target.value)}
                  className="text-xs"
                  rows={3}
                />
                <Button size="sm" onClick={handleRegrade} disabled={!clarificationText || regrading} className="w-full gap-2">
                  <RefreshCw className="h-3 w-3" />
                  {regrading ? "Regrading…" : "Request Regrade"}
                </Button>
              </div>
            </Card>
          )}

          <Button onClick={handleExport} className="w-full gap-2" size="lg">
            <Download className="h-4 w-4" />
            Export to PDF
          </Button>
        </div>
      </div>
    </div>
  );
};

export default Grading;

