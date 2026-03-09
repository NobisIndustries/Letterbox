import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { deleteTask, fetchTasks, updateTask } from "@/api/client";

export function TasksPage() {
  const [filter, setFilter] = useState<"pending" | "done" | "all">("pending");
  const queryClient = useQueryClient();

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
    <div className="flex flex-col gap-3 p-4">
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
        <p className="text-center text-sm text-muted-foreground py-8">
          Loading...
        </p>
      )}

      {tasks && tasks.length === 0 && (
        <p className="text-center text-sm text-muted-foreground py-8">
          No tasks
        </p>
      )}

      <div className="flex flex-col gap-2">
        {tasks?.map((task) => (
          <Card
            key={task.id}
            className={isOverdue(task.deadline) && !task.is_done ? "border-destructive" : ""}
          >
            <CardContent className="flex items-start gap-2 py-3">
              <input
                type="checkbox"
                checked={task.is_done}
                onChange={() =>
                  toggle.mutate({ id: task.id, isDone: !task.is_done })
                }
                className="mt-1"
              />
              <div className="flex-1 min-w-0">
                <p
                  className={`text-sm ${task.is_done ? "line-through opacity-50" : ""}`}
                >
                  {task.description}
                </p>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  {task.deadline && (
                    <span
                      className={
                        isOverdue(task.deadline) && !task.is_done
                          ? "text-destructive font-medium"
                          : ""
                      }
                    >
                      Due: {task.deadline}
                    </span>
                  )}
                  <Link
                    to={`/letters/${task.letter_id}`}
                    className="underline hover:text-primary"
                  >
                    View letter
                  </Link>
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                className="text-destructive h-6 px-1"
                onClick={() => {
                  if (confirm("Delete this task?")) remove.mutate(task.id);
                }}
              >
                ×
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
