import type { Exam, CreateQuestionPayload, Submission, ItemDetail } from "./types";

// Use relative path to leverage Vite's proxy during development
// In production, this will be the actual domain
const API_BASE = (import.meta as any).env?.VITE_API_URL || "/api";

// WebSocket URL: construct from current location in development
// This ensures WebSocket connections go through the Vite proxy
const getDefaultWsUrl = () => {
  if (typeof window !== 'undefined') {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host; // includes port
    return `${protocol}//${host}/ws/notifications/`;
  }
  return "ws://127.0.0.1:8080/ws/notifications/";
};

export const WS_URL = (import.meta as any).env?.VITE_WS_URL || getDefaultWsUrl();

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      ...(init?.headers || {}),
    },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status}: ${text || res.statusText}`);
  }
  // Some endpoints return empty on success
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) {
    const json = await res.json();
    return json as T;
  }
  return (undefined as unknown) as T;
}

// Exams
export const listExams = (): Promise<Exam[]> => request<Exam[]>(`/exams/`);

export const createExam = (payload: { name: string; topic: string; grade_level: string }): Promise<Exam> =>
  request<Exam>(`/exams/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

export const uploadExamFiles = (examId: number, files: File[]): Promise<{ image_paths: string[] }> => {
  const fd = new FormData();
  files.forEach((f) => fd.append("files", f));
  return request<{ image_paths: string[] }>(`/exams/${examId}/upload/`, { method: "POST", body: fd });
};

export const getExamImages = (examId: number): Promise<{ count: number; urls: string[] }> =>
  request<{ count: number; urls: string[] }>(`/exams/${examId}/images/`);

export const listExamQuestions = (examId: number): Promise<{ count: number; items: { id: number; label: string }[] }> =>
  request(`/exams/${examId}/questions/`);

export const createQuestion = (payload: CreateQuestionPayload) =>
  request(`/questions/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

export const solveQuestion = (questionId: number) =>
  request(`/questions/${questionId}/solve/`, { method: "POST" });

export const getQuestionSolution = (
  questionId: number
): Promise<{ answer: string; steps: unknown[]; points: number[]; generated_at: string; verified: boolean }> =>
  request(`/questions/${questionId}/solution/`);

export const verifyQuestionSolution = (questionId: number, verified: boolean) =>
  request(`/questions/${questionId}/verify/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ verified }),
  });

export const getQuestionImages = (questionId: number): Promise<{ count: number; urls: string[]; has_multiple: boolean }> =>
  request(`/questions/${questionId}/images/`);

export const deleteQuestion = (questionId: number) =>
  request(`/questions/${questionId}/`, { method: "DELETE" });

export const deleteQuestionImage = (questionId: number, imageIndex: number) =>
  request(`/questions/${questionId}/images/${imageIndex}/`, { method: "DELETE" });

export const appendQuestionImage = (questionId: number, payload: { page_index: number; bbox: any }) =>
  request(`/questions/${questionId}/append-image/`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

// Submissions
export const listSubmissions = (): Promise<Submission[]> => request(`/submissions/`);

export const createSubmission = (payload: { exam: number; student_name: string }): Promise<Submission> =>
  request(`/submissions/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

export const getSubmission = (submissionId: number): Promise<Submission> => request(`/submissions/${submissionId}/`);

export const uploadSubmissionFiles = (submissionId: number, files: File[]): Promise<{ image_paths: string[] }> => {
  const fd = new FormData();
  files.forEach((f) => fd.append("files", f));
  return request(`/submissions/${submissionId}/upload/`, { method: "POST", body: fd });
};

export const getSubmissionImages = (submissionId: number): Promise<{ count: number; urls: string[] }> =>
  request(`/submissions/${submissionId}/images/`);

export const createSubmissionItem = (submissionId: number, payload: { question_id: number; page_index: number; bbox: any }) =>
  request(`/submissions/${submissionId}/items/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

export const gradeSubmission = (submissionId: number) =>
  request(`/submissions/${submissionId}/grade/`, { method: "POST" });

export const regradeSubmission = (submissionId: number, clarify: string) =>
  request(`/submissions/${submissionId}/regrade/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ clarify }),
  });

export const gradeItem = (itemId: number): Promise<{ grading_id: number }> =>
  request(`/items/${itemId}/grade/`, { method: "POST" });

export const gradingSummary = (submissionId: number): Promise<{
  submission: number;
  student_name: string;
  items: Array<{
    item_id: number;
    question: { id: number; label: string };
    graded: boolean;
    is_correct: boolean | null;
    critical_errors: unknown;
    part_errors: unknown;
    partial_credit: unknown;
  }>;
}> => request(`/submissions/${submissionId}/grading_summary/`);

export const exportSubmission = (submissionId: number): Promise<{ pdf_url: string }> =>
  request(`/submissions/${submissionId}/export/`, { method: "POST" });

export const getItemDetail = (itemId: number): Promise<ItemDetail> => request(`/items/${itemId}/`);
export const updateItemAnnotations = (itemId: number, annotations: unknown[]) =>
  request(`/items/${itemId}/`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ annotations }),
  });

export const getSubmissionItemsList = (submissionId: number): Promise<{
  count: number;
  items: Array<{
    item_id: number;
    question_id: number;
    question_label: string;
    has_images: boolean;
    image_count: number;
    image_urls: string[];
    has_multiple_images: boolean;
  }>;
}> => request(`/submissions/${submissionId}/items-list/`);

export const deleteSubmissionItem = (itemId: number) =>
  request(`/items/${itemId}/`, { method: "DELETE" });

export const deleteSubmissionItemImage = (itemId: number, imageIndex: number) =>
  request(`/items/${itemId}/images/${imageIndex}/`, { method: "DELETE" });

export const appendSubmissionItemImage = (
  itemId: number,
  payload: { page_index: number; bbox: any }
): Promise<{ image_urls: string[]; has_multiple_images: boolean }> =>
  request(`/items/${itemId}/append-image/`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

export { API_BASE };


