import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  deleteLetter,
  fetchLetter,
  updateLetter,
  updateTask,
} from "@/api/client";
import { formatDate } from "@/lib/dateFormat";

export function LetterDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);

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
    editMutation.mutate({
      title: fd.get("title") as string,
      sender: fd.get("sender") as string,
      receiver: fd.get("receiver") as string,
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
            onClick={() => {
              if (confirm("Delete this letter?")) deleteMutation.mutate();
            }}
          >
            Delete
          </Button>
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
              <Button variant="outline" size="sm" className="w-full">
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
              <Textarea
                readOnly
                value={letter.full_text}
                className="min-h-[200px] text-xs bg-muted/40 border-0 focus-visible:ring-1"
              />
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
