import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  deleteLetter,
  fetchLetter,
  updateLetter,
  updateTask,
} from "@/api/client";

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
      setEditing(false);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteLetter(Number(id)),
    onSuccess: () => navigate("/archive"),
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
    <div className="flex flex-col gap-3 p-4 pb-20">
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
            <Input name="title" id="title" defaultValue={letter.title ?? ""} />
          </div>
          <div>
            <Label htmlFor="sender">Sender</Label>
            <Input
              name="sender"
              id="sender"
              defaultValue={letter.sender ?? ""}
            />
          </div>
          <div>
            <Label htmlFor="receiver">Receiver</Label>
            <Input
              name="receiver"
              id="receiver"
              defaultValue={letter.receiver ?? ""}
            />
          </div>
          <div>
            <Label htmlFor="keywords">Keywords</Label>
            <Input
              name="keywords"
              id="keywords"
              defaultValue={letter.keywords ?? ""}
            />
          </div>
          <div>
            <Label htmlFor="tags">Tags</Label>
            <Input name="tags" id="tags" defaultValue={letter.tags ?? ""} />
          </div>
          <Button type="submit" disabled={editMutation.isPending}>
            Save
          </Button>
        </form>
      ) : (
        <>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle>{letter.title || "Untitled"}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              {letter.sender && (
                <p>
                  <span className="text-muted-foreground">From:</span>{" "}
                  {letter.sender}
                </p>
              )}
              {letter.receiver && (
                <p>
                  <span className="text-muted-foreground">To:</span>{" "}
                  {letter.receiver}
                </p>
              )}
              {letter.creation_date && (
                <p>
                  <span className="text-muted-foreground">Date:</span>{" "}
                  {letter.creation_date}
                </p>
              )}
              {letter.keywords && (
                <p>
                  <span className="text-muted-foreground">Keywords:</span>{" "}
                  {letter.keywords}
                </p>
              )}
              {letter.tags && (
                <div className="flex flex-wrap gap-1">
                  {letter.tags.split(", ").map((tag) => (
                    <Badge key={tag} variant="secondary">
                      {tag}
                    </Badge>
                  ))}
                </div>
              )}
              {letter.summary && (
                <div>
                  <p className="text-muted-foreground mb-1">Summary</p>
                  <p>{letter.summary}</p>
                </div>
              )}
            </CardContent>
          </Card>

          {letter.pdf_path && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">PDF</CardTitle>
              </CardHeader>
              <CardContent>
                <a
                  href={`/api/letters/${letter.id}/pdf`}
                  target="_blank"
                  rel="noreferrer"
                >
                  <Button variant="outline" size="sm" className="w-full">
                    View / Download PDF
                  </Button>
                </a>
              </CardContent>
            </Card>
          )}

          {letter.tasks.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Tasks</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {letter.tasks.map((task) => (
                  <label
                    key={task.id}
                    className="flex items-start gap-2 text-sm"
                  >
                    <input
                      type="checkbox"
                      checked={task.is_done}
                      onChange={() =>
                        toggleTask.mutate({
                          taskId: task.id,
                          isDone: !task.is_done,
                        })
                      }
                      className="mt-0.5"
                    />
                    <span
                      className={task.is_done ? "line-through opacity-50" : ""}
                    >
                      {task.description}
                      {task.deadline && (
                        <span className="ml-1 text-muted-foreground">
                          (due {task.deadline})
                        </span>
                      )}
                    </span>
                  </label>
                ))}
              </CardContent>
            </Card>
          )}

          {letter.full_text && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Full Text</CardTitle>
              </CardHeader>
              <CardContent>
                <Textarea
                  readOnly
                  value={letter.full_text}
                  className="min-h-[200px] text-xs"
                />
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
