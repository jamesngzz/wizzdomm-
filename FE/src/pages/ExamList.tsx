import { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { FileText, Plus, Scissors, Users } from "lucide-react";
import { Link } from "react-router-dom";
import { listExams } from "@/lib/api";
import type { Exam } from "@/lib/types";

const ExamList = () => {
  const [exams, setExams] = useState<Exam[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | "">("");

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const data = await listExams();
        if (mounted) setExams(data);
      } catch (e: any) {
        if (mounted) setError(e?.message || "Failed to load exams");
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Exam Management</h1>
          <p className="mt-2 text-muted-foreground">All created exams</p>
        </div>
        <Button asChild className="gap-2">
          <Link to="/exams/create">
            <Plus className="h-4 w-4" />
            Create New Exam
          </Link>
        </Button>
      </div>

      {loading && <p className="text-sm text-muted-foreground">Loading exams…</p>}
      {error && !loading && (
        <p className="text-sm text-red-600">{error}</p>
      )}
      {!loading && !error && (
        <div className="grid gap-4">
          {exams.length === 0 && (
            <Card className="p-6">
              <p className="text-sm text-muted-foreground">No exams yet. Create one to get started.</p>
            </Card>
          )}
          {exams.map((exam) => (
            <Card key={exam.id} className="p-6 hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-foreground mb-1">{exam.name}</h3>
                  <p className="text-sm text-muted-foreground mb-3">{exam.topic}</p>
                  <div className="flex gap-2 items-center">
                    <Badge variant="secondary">Grade {exam.grade_level}</Badge>
                    <Badge variant="outline">ID: {exam.id}</Badge>
                  </div>
                </div>
                <FileText className="h-8 w-8 text-primary opacity-50" />
              </div>
              <div className="flex gap-2 pt-3 border-t border-border">
                <Button asChild variant="default" size="sm" className="flex-1 gap-2">
                  <Link to={`/exams/crop?examId=${exam.id}`}>
                    <Scissors className="h-4 w-4" />
                    Manage Questions
                  </Link>
                </Button>
                <Button asChild variant="outline" size="sm" className="flex-1 gap-2">
                  <Link to={`/submissions?examId=${exam.id}`}>
                    <Users className="h-4 w-4" />
                    View Submissions
                  </Link>
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};

export default ExamList;
