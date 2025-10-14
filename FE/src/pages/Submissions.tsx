import { useEffect, useState, useMemo } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Upload, FileCheck, Loader2, ArrowLeft, ChevronDown, ChevronRight } from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { createSubmission, listExams, listSubmissions, uploadSubmissionFiles } from "@/lib/api";
import type { Exam, Submission } from "@/lib/types";

const Submissions = () => {
  const [sp] = useSearchParams();
  const filterExamId = sp.get("examId");
  
  const [studentName, setStudentName] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [exams, setExams] = useState<Exam[]>([]);
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [examId, setExamId] = useState<string>(filterExamId || "");
  const [expandedExamIds, setExpandedExamIds] = useState<Set<number>>(new Set());
  const [uploading, setUploading] = useState(false);

  const loadData = async () => {
    try {
      const [examsData, subsData] = await Promise.all([listExams(), listSubmissions()]);
      setExams(examsData);
      setSubmissions(subsData);
    } catch (e: any) {
      toast.error(e?.message || "Failed to load submissions");
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const filteredSubmissions = useMemo(() => {
    if (!filterExamId) return submissions;
    return submissions.filter((s) => s.exam === Number(filterExamId));
  }, [submissions, filterExamId]);

  const currentExam = useMemo(() => {
    if (!filterExamId) return null;
    return exams.find((e) => e.id === Number(filterExamId));
  }, [exams, filterExamId]);

  // Group submissions by exam
  const groups = useMemo(() => {
    const map = new Map<number, { exam: Exam | undefined; items: Submission[] }>();
    for (const s of filteredSubmissions) {
      if (!map.has(s.exam)) map.set(s.exam, { exam: exams.find((e) => e.id === s.exam), items: [] });
      map.get(s.exam)!.items.push(s);
    }
    // Initialize expanded set: expand selected exam if filter exists; otherwise expand all
    if (expandedExamIds.size === 0) {
      const initial = new Set<number>();
      if (filterExamId) initial.add(Number(filterExamId));
      else for (const id of map.keys()) initial.add(id);
      setExpandedExamIds(initial);
    }
    return Array.from(map.entries()).sort((a, b) => {
      const an = a[1].exam?.name || String(a[0]);
      const bn = b[1].exam?.name || String(b[0]);
      return an.localeCompare(bn);
    });
  }, [filteredSubmissions, exams, filterExamId]);

  const getStatusBadge = (s: Submission) => {
    // MVP: Derive a coarse status from images presence only.
    const hasImages = (s.original_image_paths || []).length > 0;
    const label = hasImages ? "Ready to Crop" : "Awaiting Upload";
    const icon = hasImages ? <FileCheck className="h-3 w-3" /> : <Loader2 className="h-3 w-3 animate-spin" />;
    const variant = hasImages ? ("default" as const) : ("secondary" as const);
    return (
      <Badge variant={variant} className="gap-1">
        {icon}
        {label}
      </Badge>
    );
  };

  const handleUpload = async (files: FileList | null) => {
    if (!files || !studentName || !examId) {
      toast.error("Please select exam, enter student name and choose files");
      return;
    }
    try {
      setUploading(true);
      const submission = await createSubmission({ exam: Number(examId), student_name: studentName });
      await uploadSubmissionFiles(submission.id, Array.from(files));
      toast.success(`Uploaded ${files.length} files for ${studentName}. Upscaling will start automatically.`);
      setDialogOpen(false);
      setStudentName("");
      setExamId("");
      await loadData();
    } catch (e: any) {
      toast.error(e?.message || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  // When user clicks grading or crop, also register a sidebar tab
  const addSidebarTab = (type: "grading" | "crop", submissionId: number, examName?: string, studentName?: string) => {
    const key = type === "grading" ? "sidebar:gradingTabs" : "sidebar:cropTabs";
    const MAX_TABS = 10;
    try {
      const raw = localStorage.getItem(key);
      const arr = raw ? JSON.parse(raw) : [];
      const exists = Array.isArray(arr) && arr.some((t: any) => t && t.id === submissionId);
      if (!exists) {
        const label = studentName ? `${studentName}` : examName ? `${examName}` : `#${submissionId}`;
        let next = Array.isArray(arr) ? [...arr, { id: submissionId, label }] : [{ id: submissionId, label }];
        if (next.length > MAX_TABS) next = next.slice(-MAX_TABS);
        localStorage.setItem(key, JSON.stringify(next));
        // Fire a storage event manually so other tabs/components react immediately
        try {
          window.dispatchEvent(new StorageEvent('storage', { key, newValue: JSON.stringify(next) } as any));
        } catch {}
      }
    } catch {}
  };

  return (
    <div className="space-y-6">
      {currentExam && (
        <Button variant="ghost" size="sm" asChild className="gap-2">
          <Link to="/exams">
            <ArrowLeft className="h-4 w-4" />
            Back to Exam List
          </Link>
        </Button>
      )}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Student Submissions</h1>
          <p className="mt-2 text-muted-foreground">
            {filteredSubmissions.length} submission{filteredSubmissions.length !== 1 ? 's' : ''}
            {currentExam && <span className="ml-2 font-medium">for {currentExam.name}</span>}
          </p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button className="gap-2">
              <Upload className="h-4 w-4" />
              Upload Submission
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Upload Student Submission</DialogTitle>
              <DialogDescription>
                Select an exam, enter the student name, and upload their submission images.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 pt-4">
              <div>
                <label className="text-sm font-medium">Exam</label>
                <Select value={examId} onValueChange={setExamId}>
                  <SelectTrigger className="mt-2">
                    <SelectValue placeholder="Select exam" />
                  </SelectTrigger>
                  <SelectContent>
                    {exams.map((ex) => (
                      <SelectItem key={ex.id} value={String(ex.id)}>
                        {ex.name} (#{ex.id})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="text-sm font-medium">Student Name</label>
                <Input
                  placeholder="Enter student name"
                  value={studentName}
                  onChange={(e) => setStudentName(e.target.value)}
                  className="mt-2"
                />
              </div>
              <div>
                <label className="text-sm font-medium">Upload Images/PDF</label>
                <Input
                  type="file"
                  multiple
                  accept="image/*,.pdf,application/pdf"
                  onChange={(e) => handleUpload(e.target.files)}
                  className="mt-2"
                />
              </div>
              {uploading && (
                <div className="text-xs text-muted-foreground">Uploading…</div>
              )}
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <div className="space-y-4">
        {groups.map(([examIdNum, group]) => {
          const isOpen = expandedExamIds.has(examIdNum);
          return (
            <Card key={examIdNum} className="p-0 overflow-hidden">
              <div
                className="flex items-center justify-between px-4 py-3 border-b cursor-pointer hover:bg-muted/30"
                onClick={() => {
                  const next = new Set(expandedExamIds);
                  if (isOpen) next.delete(examIdNum); else next.add(examIdNum);
                  setExpandedExamIds(next);
                }}
              >
                <div className="flex items-center gap-3">
                  {isOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                  <h2 className="text-base font-semibold text-foreground">
                    {group.exam?.name || `Exam #${examIdNum}`}
                  </h2>
                  <Badge variant="secondary" className="text-xs">{group.items.length} submission{group.items.length !== 1 ? 's' : ''}</Badge>
                </div>
                {group.exam && (
                  <span className="text-xs text-muted-foreground">ID: {group.exam.id}</span>
                )}
              </div>
              {isOpen && (
                <div className="p-4">
                  <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {group.items.map((submission) => (
                      <Card key={submission.id} className="p-6 hover:shadow-md transition-shadow">
                        <div className="space-y-4">
                          <div className="flex items-start justify-between">
                            <div className="flex-1">
                              <h3 className="text-lg font-semibold text-foreground mb-1">
                                {submission.student_name}
                              </h3>
                              <p className="text-sm text-muted-foreground">
                                Images: {(submission.original_image_paths || []).length}
                              </p>
                            </div>
                          </div>
                          {getStatusBadge(submission)}
                          <div className="space-y-2 pt-2">
                            <Button
                              variant="outline"
                              size="sm"
                              className="w-full"
                              onClick={() => {
                                try {
                                  window.dispatchEvent(new CustomEvent("ta:add-tab", { detail: { which: "crop", id: submission.id, label: submission.student_name || currentExam?.name } }));
                                } catch {}
                                // Use SPA navigation to avoid full reloads that may reset transient state
                                window.history.pushState({}, '', `/submissions/crop?submissionId=${submission.id}`);
                                window.dispatchEvent(new PopStateEvent('popstate'));
                              }}
                            >
                              Crop Answers
                            </Button>
                            <Button
                              size="sm"
                              className="w-full"
                              variant="secondary"
                              onClick={() => {
                                try {
                                  window.dispatchEvent(new CustomEvent("ta:add-tab", { detail: { which: "grading", id: submission.id, label: submission.student_name || currentExam?.name } }));
                                } catch {}
                                window.history.pushState({}, '', `/grading?submissionId=${submission.id}`);
                                window.dispatchEvent(new PopStateEvent('popstate'));
                              }}
                            >
                              Review Grading
                            </Button>
                          </div>
                        </div>
                      </Card>
                    ))}
                  </div>
                </div>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
};

export default Submissions;
