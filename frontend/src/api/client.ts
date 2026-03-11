import type {
  IngestResponse,
  Letter,
  LetterListResponse,
  Setting,
  Task,
  Translation,
} from "@/types";

const BASE = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  if (!res.ok) {
    throw new Error(`${res.status}: ${await res.text()}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// Letters
export async function fetchLetters(params: {
  q?: string;
  date_from?: string;
  date_to?: string;
  tag?: string;
  receiver?: string;
  offset?: number;
  limit?: number;
  order?: string;
}): Promise<LetterListResponse> {
  const sp = new URLSearchParams();
  if (params.q) sp.set("q", params.q);
  if (params.date_from) sp.set("date_from", params.date_from);
  if (params.date_to) sp.set("date_to", params.date_to);
  if (params.tag) sp.set("tag", params.tag);
  if (params.receiver) sp.set("receiver", params.receiver);
  if (params.offset !== undefined) sp.set("offset", String(params.offset));
  if (params.limit !== undefined) sp.set("limit", String(params.limit));
  if (params.order) sp.set("order", params.order);
  return request<LetterListResponse>(`/letters?${sp}`);
}

export async function fetchReceivers(): Promise<string[]> {
  return request<string[]>("/receivers");
}

export async function fetchLetter(id: number): Promise<Letter> {
  return request<Letter>(`/letters/${id}`);
}

export async function updateLetter(
  id: number,
  data: Partial<Letter>
): Promise<Letter> {
  return request<Letter>(`/letters/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteLetter(id: number): Promise<void> {
  return request<void>(`/letters/${id}`, { method: "DELETE" });
}

// Ingest
export async function uploadImages(files: File[]): Promise<IngestResponse> {
  const formData = new FormData();
  for (const f of files) {
    formData.append("files", f);
  }
  const res = await fetch(`${BASE}/letters/ingest`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
  return res.json();
}

// Tasks
export async function fetchTasks(
  filter: "all" | "pending" | "done" = "all",
  recipient?: string
): Promise<Task[]> {
  const params = new URLSearchParams({ filter });
  if (recipient) params.set("recipient", recipient);
  return request<Task[]>(`/tasks?${params}`);
}

export async function updateTask(
  id: number,
  data: Partial<Task>
): Promise<Task> {
  return request<Task>(`/tasks/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteTask(id: number): Promise<void> {
  return request<void>(`/tasks/${id}`, { method: "DELETE" });
}

// Settings
export async function fetchSetting(key: string): Promise<Setting> {
  return request<Setting>(`/settings/${key}`);
}

export async function updateSetting(
  key: string,
  value: string[]
): Promise<Setting> {
  return request<Setting>(`/settings/${key}`, {
    method: "PUT",
    body: JSON.stringify({ value }),
  });
}

// Senders
export async function fetchSenders(): Promise<string[]> {
  return request<string[]>("/senders");
}

// Translations
export async function fetchTranslation(
  letterId: number,
  language: string
): Promise<Translation> {
  return request<Translation>(`/letters/${letterId}/translations/${encodeURIComponent(language)}`);
}

export async function createTranslation(
  letterId: number,
  language: string
): Promise<Translation> {
  return request<Translation>(
    `/letters/${letterId}/translations/${encodeURIComponent(language)}`,
    { method: "POST" }
  );
}
