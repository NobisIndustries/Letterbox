import { useState, useRef } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  createTranslation,
  deleteLetter,
  fetchLetter,
  fetchSetting,
  updateLetter,
  updateTask,
} from "@/api/client";
import { formatDate } from "@/lib/dateFormat";
import { ConfirmDialog } from "@/components/ConfirmDialog";

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  const timeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleCopy = () => {
    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(text).then(() => {
        setCopied(true);
        if (timeout.current) clearTimeout(timeout.current);
        timeout.current = setTimeout(() => setCopied(false), 2000);
      }).catch(() => fallbackCopy());
    } else {
      fallbackCopy();
    }
  };

  const fallbackCopy = () => {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.cssText = "position:fixed;top:0;left:0;opacity:0";
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    try {
      document.execCommand("copy");
      setCopied(true);
      if (timeout.current) clearTimeout(timeout.current);
      timeout.current = setTimeout(() => setCopied(false), 2000);
    } finally {
      document.body.removeChild(ta);
    }
  };

  return (
    <button
      onClick={handleCopy}
      className="absolute top-1 right-1 z-10 rounded p-2 text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
      title="Copy to clipboard"
    >
      {copied ? (
        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-green-800" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
          <polyline points="20 6 9 17 4 12" />
        </svg>
      ) : (
        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <rect x="9" y="9" width="13" height="13" rx="2" />
          <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
        </svg>
      )}
    </button>
  );
}

export function LetterDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [selectedLanguage, setSelectedLanguage] = useState<string | null>(null);

  const { data: letter, isLoading } = useQuery({
    queryKey: ["letter", id],
    queryFn: () => fetchLetter(Number(id)),
    enabled: !!id,
  });

  const editMutation = useMutation({
    mutationFn: (data: Parameters<typeof updateLetter>[1]) =>
      updateLetter(Number(id), data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["letter", id] });
      queryClient.invalidateQueries({ queryKey: ["letters"] });
      setEditing(false);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteLetter(Number(id)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["letters"] });
      navigate("/archive");
    },
  });

  const { data: languagesSetting } = useQuery({
    queryKey: ["settings", "translation_languages"],
    queryFn: () => fetchSetting("translation_languages"),
  });
  const languages = languagesSetting?.value ?? [];

  const { data: translation, isLoading: translationLoading } = useQuery({
    queryKey: ["translation", id, selectedLanguage],
    queryFn: () => createTranslation(Number(id), selectedLanguage!),
    enabled: !!selectedLanguage,
    retry: false,
    staleTime: Infinity,
  });

  const toggleTask = useMutation({
    mutationFn: ({ taskId, isDone }: { taskId: number; isDone: boolean }) =>
      updateTask(taskId, { is_done: isDone }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["letter", id] });
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
  });

  if (isLoading || !letter) {
    return <p className="p-4 text-center text-muted-foreground">Loading...</p>;
  }

  const handleSave = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const dateVal = fd.get("creation_date") as string;
    editMutation.mutate({
      title: fd.get("title") as string,
      sender: fd.get("sender") as string,
      receiver: fd.get("receiver") as string,
      creation_date: dateVal || null,
      summary: fd.get("summary") as string,
      keywords: fd.get("keywords") as string,
      tags: fd.get("tags") as string,
    });
  };

  return (
    <div className="md:flex md:h-screen md:overflow-hidden">
    {/* Left: metadata */}
    <div className="flex flex-col gap-4 p-4 pb-20 md:pb-4 md:w-1/2 md:overflow-y-auto md:border-r">
      <div className="flex items-center justify-between">
        <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
          ← Back
        </Button>
        <div className="flex gap-1">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setEditing(!editing)}
          >
            {editing ? "Cancel" : "Edit"}
          </Button>
          <Button
            variant="destructive"
            size="sm"
            onClick={() => setConfirmDelete(true)}
          >
            Delete
          </Button>
          <ConfirmDialog
            open={confirmDelete}
            onOpenChange={setConfirmDelete}
            title="Delete this letter?"
            description="This will permanently remove the letter and its PDF."
            onConfirm={() => deleteMutation.mutate()}
          />
        </div>
      </div>

      {editing ? (
        <form onSubmit={handleSave} className="flex flex-col gap-3">
          <div>
            <Label htmlFor="title">Title</Label>
            <Input name="title" id="title" defaultValue={letter.title ?? ""} className="bg-muted border-0 focus-visible:ring-1" />
          </div>
          <div>
            <Label htmlFor="sender">Sender</Label>
            <Input name="sender" id="sender" defaultValue={letter.sender ?? ""} className="bg-muted border-0 focus-visible:ring-1" />
          </div>
          <div>
            <Label htmlFor="receiver">Receiver</Label>
            <Input name="receiver" id="receiver" defaultValue={letter.receiver ?? ""} className="bg-muted border-0 focus-visible:ring-1" />
          </div>
          <div>
            <Label htmlFor="creation_date">Date</Label>
            <Input name="creation_date" id="creation_date" type="date" defaultValue={letter.creation_date ?? ""} className="bg-muted border-0 focus-visible:ring-1" />
          </div>
          <div>
            <Label htmlFor="summary">Summary</Label>
            <Textarea name="summary" id="summary" defaultValue={letter.summary ?? ""} className="bg-muted border-0 focus-visible:ring-1" />
          </div>
          <div>
            <Label htmlFor="keywords">Keywords</Label>
            <Input name="keywords" id="keywords" defaultValue={letter.keywords ?? ""} className="bg-muted border-0 focus-visible:ring-1" />
          </div>
          <div>
            <Label htmlFor="tags">Tags</Label>
            <Input name="tags" id="tags" defaultValue={letter.tags ?? ""} className="bg-muted border-0 focus-visible:ring-1" />
          </div>
          <Button type="submit" disabled={editMutation.isPending}>
            Save
          </Button>
        </form>
      ) : (
        <>
          <h1 className="text-xl font-semibold">{letter.title || "Untitled"}</h1>

          <div className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 text-sm">
            {letter.sender && (
              <>
                <span className="text-muted-foreground">From</span>
                <span>{letter.sender}</span>
              </>
            )}
            {letter.receiver && (
              <>
                <span className="text-muted-foreground">To</span>
                <span>{letter.receiver}</span>
              </>
            )}
            {letter.creation_date && (
              <>
                <span className="text-muted-foreground">Date</span>
                <span>{formatDate(letter.creation_date)}</span>
              </>
            )}
            {letter.keywords && (
              <>
                <span className="text-muted-foreground">Keywords</span>
                <span>{letter.keywords}</span>
              </>
            )}
          </div>

          {letter.tags && (
            <div className="flex flex-wrap gap-1.5">
              {letter.tags.split(", ").map((tag) => (
                <span
                  key={tag}
                  className="text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary font-medium"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}

          {letter.summary && (
            <div>
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-1.5">Summary</p>
              <div className="rounded-lg bg-muted/60 p-3 text-sm">
                {letter.summary}
              </div>
            </div>
          )}

          {letter.pdf_path && (
            <a
              href={`/api/letters/${letter.id}/pdf`}
              target="_blank"
              rel="noreferrer"
              className="md:hidden"
            >
              <Button variant="outline" size="sm" className="w-full bg-green-800 text-white border-green-800 hover:bg-green-900 hover:border-green-900 hover:text-white">
                View / Download PDF
              </Button>
            </a>
          )}

          {letter.tasks.length > 0 && (
            <div>
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">Tasks</p>
              <div className="flex flex-col gap-2">
                {letter.tasks.map((task) => (
                  <label
                    key={task.id}
                    className="flex items-start gap-3 text-sm cursor-pointer"
                  >
                    <span
                      onClick={() =>
                        toggleTask.mutate({
                          taskId: task.id,
                          isDone: !task.is_done,
                        })
                      }
                      className={`mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border text-[10px] transition-colors ${
                        task.is_done
                          ? "bg-primary border-primary text-primary-foreground"
                          : "border-muted-foreground text-transparent"
                      }`}
                    >
                      ✓
                    </span>
                    <span
                      className={task.is_done ? "line-through opacity-50" : ""}
                    >
                      {task.description}
                      {task.deadline && (
                        <span className="ml-1 text-muted-foreground">
                          (due {formatDate(task.deadline)})
                        </span>
                      )}
                    </span>
                  </label>
                ))}
              </div>
            </div>
          )}

          {letter.full_text && (
            <div>
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-1.5">Transcript</p>

              {languages.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mb-2">
                  <button
                    onClick={() => setSelectedLanguage(null)}
                    className={`text-xs px-3 py-1 rounded-full border transition-colors ${
                      selectedLanguage === null
                        ? "bg-green-800 text-white border-green-800"
                        : "border-border hover:border-muted-foreground/50"
                    }`}
                  >
                    Original
                  </button>
                  {languages.map((lang) => (
                    <button
                      key={lang}
                      onClick={() => setSelectedLanguage(lang)}
                      className={`text-xs px-3 py-1 rounded-full border transition-colors ${
                        selectedLanguage === lang
                          ? "bg-green-800 text-white border-green-800"
                          : "border-border hover:border-muted-foreground/50"
                      }`}
                    >
                      {lang}
                    </button>
                  ))}
                </div>
              )}

              {selectedLanguage === null ? (
                <div className="relative">
                  <CopyButton text={letter.full_text} />
                  <Textarea
                    readOnly
                    value={letter.full_text}
                    className="min-h-[200px] text-xs bg-muted/40 border-0 focus-visible:ring-1"
                  />
                </div>
              ) : translationLoading ? (
                <div className="flex flex-col items-center justify-center gap-3 py-16">
                  <svg className="h-10 w-10 animate-spin text-muted-foreground" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  <p className="text-sm text-muted-foreground">Translating to {selectedLanguage}…</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {translation?.translated_summary && (
                    <div className="rounded-lg bg-muted/60 p-3 text-sm">
                      {translation.translated_summary}
                    </div>
                  )}
                  {translation?.translated_text && (
                    <div className="relative">
                      <CopyButton text={translation.translated_text} />
                      <Textarea
                        readOnly
                        value={translation.translated_text}
                        className="min-h-[200px] text-xs bg-muted/40 border-0 focus-visible:ring-1"
                      />
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>

    {/* Right: PDF (desktop only) */}
    {letter.pdf_path && (
      <div className="hidden md:block md:w-1/2 p-4 bg-muted/30">
        <iframe
          src={`/api/letters/${letter.id}/pdf`}
          className="w-full h-full rounded-lg"
          title="Letter PDF"
        />
      </div>
    )}
    </div>
  );
}
