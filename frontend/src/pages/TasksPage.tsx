import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { deleteTask, fetchTasks, updateTask } from "@/api/client";

export function TasksPage() {
  const [filter, setFilter] = useState<"pending" | "done" | "all">("pending");
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const { data: tasks, isLoading } = useQuery({
    queryKey: ["tasks", filter],
    queryFn: () => fetchTasks(filter),
  });

  const toggle = useMutation({
    mutationFn: ({ id, isDone }: { id: number; isDone: boolean }) =>
      updateTask(id, { is_done: isDone }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["tasks"] }),
  });

  const remove = useMutation({
    mutationFn: (id: number) => deleteTask(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["tasks"] }),
  });

  const isOverdue = (deadline: string | null) =>
    deadline && new Date(deadline) < new Date();

  return (
    <div className="flex flex-col gap-3 p-4 max-w-2xl mx-auto">
      <h1 className="text-lg font-semibold">Tasks</h1>

      <div className="flex gap-1">
        {(["pending", "done", "all"] as const).map((f) => (
          <Button
            key={f}
            variant={filter === f ? "default" : "outline"}
            size="sm"
            onClick={() => setFilter(f)}
          >
            {f.charAt(0).toUpperCase() + f.slice(1)}
          </Button>
        ))}
      </div>

      {isLoading && (
        <p className="text-center text-sm text-muted-foreground py-8">Loading...</p>
      )}

      {tasks && tasks.length === 0 && (
        <p className="text-center text-sm text-muted-foreground py-8">No tasks</p>
      )}

      <div className="flex flex-col gap-2">
        {tasks?.map((task) => (
          <div
            key={task.id}
            className={`flex items-stretch rounded-xl bg-card shadow-sm overflow-hidden ${
              isOverdue(task.deadline) && !task.is_done ? "border-l-2 border-l-destructive" : ""
            }`}
          >
            {/* Checkbox — tall touch target, full left column */}
            <button
              onClick={() => toggle.mutate({ id: task.id, isDone: !task.is_done })}
              className={`flex items-center justify-center w-14 shrink-0 transition-colors ${
                task.is_done
                  ? "bg-primary/10 text-primary"
                  : "hover:bg-muted text-muted-foreground"
              }`}
              aria-label={task.is_done ? "Mark as pending" : "Mark as done"}
            >
              <span className={`flex h-6 w-6 items-center justify-center rounded-full border-2 text-sm font-bold transition-colors ${
                task.is_done
                  ? "border-primary bg-primary text-primary-foreground"
                  : "border-muted-foreground"
              }`}>
                {task.is_done && "✓"}
              </span>
            </button>

            {/* Task body — clicking navigates to letter */}
            <button
              className="flex-1 min-w-0 text-left px-3 py-3 hover:bg-muted/40 transition-colors"
              onClick={() => navigate(`/letters/${task.letter_id}`)}
            >
              <div className="flex items-start justify-between gap-2">
                <p className={`text-sm leading-snug ${task.is_done ? "line-through opacity-50" : ""}`}>
                  {task.description}
                </p>
                {task.letter_receiver && (
                  <span className="text-xs font-medium text-primary shrink-0">
                    {task.letter_receiver}
                  </span>
                )}
              </div>
              <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 mt-1 text-xs text-muted-foreground">
                {task.letter_sender && <span>{task.letter_sender}</span>}
                {task.deadline && (
                  <span className={isOverdue(task.deadline) && !task.is_done ? "text-destructive font-medium" : ""}>
                    Due: {task.deadline}
                  </span>
                )}
              </div>
            </button>

            {/* Delete */}
            <button
              className="flex items-center justify-center w-10 shrink-0 text-muted-foreground hover:text-destructive hover:bg-muted/40 transition-colors text-lg"
              onClick={() => { if (confirm("Delete this task?")) remove.mutate(task.id); }}
              aria-label="Delete task"
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
