export interface Task {
  id: number;
  letter_id: number;
  description: string;
  deadline: string | null;
  is_done: boolean;
  created_at: string;
  letter_title: string | null;
  letter_sender: string | null;
  letter_receiver: string | null;
}

export interface Letter {
  id: number;
  title: string | null;
  summary: string | null;
  sender: string | null;
  receiver: string | null;
  creation_date: string | null;
  ingested_at: string;
  keywords: string | null;
  tags: string | null;
  full_text: string | null;
  pdf_path: string | null;
  page_count: number | null;
  tasks: Task[];
}

export interface LetterListItem {
  id: number;
  title: string | null;
  summary: string | null;
  sender: string | null;
  receiver: string | null;
  creation_date: string | null;
  ingested_at: string;
  keywords: string | null;
  tags: string | null;
  page_count: number | null;
}

export interface LetterListResponse {
  items: LetterListItem[];
  total: number;
}

export interface IngestResponse {
  job_id: string;
}

export interface JobStatus {
  status: string;
  letter_id: number | null;
  error: string | null;
  duplicate_of: number | null;
  created_at: number;
}

export interface Setting {
  key: string;
  value: string[];
}

export interface Translation {
  id: number;
  letter_id: number;
  language: string;
  translated_text: string | null;
  translated_summary: string | null;
  created_at: string;
}
