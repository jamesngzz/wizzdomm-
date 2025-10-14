import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Upload, FileText, ArrowRight } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { createExam, uploadExamFiles } from "@/lib/api";

const CreateExam = () => {
  const navigate = useNavigate();
  const [examName, setExamName] = useState("");
  const [grade, setGrade] = useState("");
  const [subject, setSubject] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [submitting, setSubmitting] = useState(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFiles(Array.from(e.target.files));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!examName || !grade || !subject || files.length === 0) {
      toast.error("Vui lòng điền đầy đủ thông tin");
      return;
    }
    try {
      setSubmitting(true);
      const exam = await createExam({ name: examName, topic: subject, grade_level: grade });
      await uploadExamFiles(exam.id, files);
      toast.success("Đề thi đã được tạo và tải lên thành công!");
      setExamName("");
      setGrade("");
      setSubject("");
      setFiles([]);
      navigate(`/exams/crop?examId=${exam.id}`);
    } catch (err: any) {
      toast.error(err?.message || "Tạo đề thi thất bại");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground flex items-center gap-3">
          <FileText className="h-8 w-8 text-primary" />
          Tạo đề thi mới
        </h1>
        <p className="mt-2 text-muted-foreground">
          Bắt đầu bằng cách tải lên hình ảnh đề thi và nhập thông tin cơ bản.
        </p>
      </div>

      <form onSubmit={handleSubmit}>
        <Card className="p-8">
          <div className="mb-6">
            <h2 className="text-lg font-semibold text-foreground flex items-center gap-2 mb-4">
              <FileText className="h-5 w-5 text-primary" />
              Thông tin đề thi
            </h2>
            <div className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="exam-name">Tên đề thi*</Label>
                  <Input
                    id="exam-name"
                    placeholder="vd: Kiểm tra giữa kỳ 1"
                    value={examName}
                    onChange={(e) => setExamName(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="grade">Khối lớp*</Label>
                  <Select value={grade} onValueChange={setGrade}>
                    <SelectTrigger id="grade">
                      <SelectValue placeholder="Chọn khối lớp" />
                    </SelectTrigger>
                    <SelectContent>
                      {[6, 7, 8, 9, 10, 11, 12].map((g) => (
                        <SelectItem key={g} value={`${g}`}>
                          Lớp {g}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="subject">Chủ đề*</Label>
                <Input
                  id="subject"
                  placeholder="vd: Phương trình bậc hai, Hình học"
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                />
              </div>
            </div>
          </div>

          <div className="border-t border-border pt-6">
            <h2 className="text-lg font-semibold text-foreground flex items-center gap-2 mb-4">
              <Upload className="h-5 w-5 text-primary" />
              Tải lên đề thi
            </h2>
            <div className="space-y-4">
              <Label>Tải lên đề thi (ảnh hoặc PDF)*</Label>
              <div className="relative">
                <input
                  type="file"
                  multiple
                  accept="image/*,.pdf"
                  onChange={handleFileChange}
                  className="hidden"
                  id="file-upload"
                />
                <label
                  htmlFor="file-upload"
                  className="flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-border bg-muted/30 p-12 transition-colors hover:bg-muted/50"
                >
                  <Upload className="mb-4 h-12 w-12 text-muted-foreground" />
                  <p className="mb-2 text-sm font-medium text-foreground">
                    Drag and drop files here
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Limit 200MB per file • PNG, JPG, JPEG, PDF
                  </p>
                  <Button type="button" variant="outline" className="mt-4" size="sm" asChild>
                    {/* Clicking this triggers the hidden file input via label */}
                    Browse files
                  </Button>
                </label>
              </div>
              {files.length > 0 && (
                <div className="space-y-2">
                  <p className="text-sm font-medium text-foreground">
                    Đã chọn {files.length} file:
                  </p>
                  <div className="space-y-2">
                    {files.map((file, idx) => (
                      <div
                        key={idx}
                        className="flex items-center gap-2 rounded-lg border border-border bg-muted/30 p-3"
                      >
                        <FileText className="h-5 w-5 text-primary" />
                        <span className="text-sm text-foreground">{file.name}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="mt-8 flex justify-end gap-3">
            <Button type="button" variant="outline" onClick={() => navigate("/")} disabled={submitting}>
              Hủy
            </Button>
            <Button type="submit" className="gap-2" disabled={submitting}>
              Tạo đề thi
              <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        </Card>
      </form>
    </div>
  );
};

export default CreateExam;
