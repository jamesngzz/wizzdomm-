// Shared frontend types aligned with the Django backend serializers/models

export type ISODateString = string;

export interface Exam {
  id: number;
  name: string;
  topic: string;
  grade_level: string;
  original_image_paths?: string[] | null;
  created_at: ISODateString;
}

export interface Question {
  id: number;
  exam: number;
  order_index: number;
  part_label: string | null;
  question_image_paths?: string[] | null;
  has_multiple_images: boolean;
  solution_answer?: string | null;
  solution_steps?: unknown[] | null;
  solution_points?: number[] | null;
  solution_verified?: boolean;
  solution_generated_at?: ISODateString | null;
}

export type BBoxNormalized = {
  // 0..1 relative to original image dimensions
  x: number;
  y: number;
  w: number;
  h: number;
  normalized?: true;
};

export interface CreateQuestionPayload {
  exam: number; // exam id
  label: string; // e.g., "1a"
  page_index: number;
  bbox: BBoxNormalized; // FE sends normalized bbox
}

export interface Submission {
  id: number;
  exam: number; // exam id
  student_name: string;
  original_image_paths?: string[] | null;
  created_at: ISODateString;
}

export interface ItemDetail {
  id: number;
  submission_id: number;
  question_id: number;
  question_label: string;
  source_page_indices: number[];
  answer_image_paths: string[];
  answer_image_urls: string[];
  answer_bbox?: Record<string, unknown> | null;
  original_image_dimensions?: { width: number; height: number } | null;
  annotations?: unknown[] | null;
  grading?: {
    is_correct: boolean | null;
    critical_errors: unknown;
    part_errors: unknown;
    partial_credit: unknown;
  } | null;
}


