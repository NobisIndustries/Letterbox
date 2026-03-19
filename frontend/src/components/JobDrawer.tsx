import { useState } from "react";
import { Loader2, X, ListTodo, Trash2 } from "lucide-react";
import { clearFinishedJobs } from "@/api/client";
import { JobStatusPanel } from "@/components/JobStatusPanel";
import type { JobStatus } from "@/types";

const TERMINAL = new Set(["done", "error", "skipped"]);

interface JobDrawerProps {
  jobs: Record<string, JobStatus>;
  onRefresh: () => void;
}

export function JobDrawer({ jobs, onRefresh }: JobDrawerProps) {
  const [open, setOpen] = useState(false);

  const count = Object.keys(jobs).length;
  const activeCount = Object.values(jobs).filter((j) => !TERMINAL.has(j.status)).length;
  const hasFinished = count > activeCount;

  async function handleClear() {
    await clearFinishedJobs();
    onRefresh();
  }

  return (
    <>
      {/* Toggle button — desktop: right edge tab, mobile: pill above bottom nav */}
      {count > 0 && (
        <button
          onClick={() => setOpen(true)}
          className={`
            fixed z-40
            md:right-0 md:top-1/2 md:-translate-y-1/2 md:rounded-l-lg md:rounded-r-none md:px-1.5 md:py-3 md:flex-col
            bottom-[4.5rem] right-3 md:bottom-auto
            flex items-center gap-1.5 rounded-full md:rounded-full-none px-3 py-2
            bg-primary text-primary-foreground shadow-lg text-sm font-medium
          `}
        >
          {activeCount > 0 ? (
            <Loader2 size={14} className="animate-spin" />
          ) : (
            <ListTodo size={14} />
          )}
          <span className="md:hidden">
            {activeCount > 0 ? `${activeCount} processing` : `${count} jobs`}
          </span>
          {/* Desktop: vertical label */}
          <span
            className="hidden md:block text-xs"
            style={{ writingMode: "vertical-rl", textOrientation: "mixed" }}
          >
            {activeCount > 0 ? `${activeCount} active` : "Jobs"}
          </span>
        </button>
      )}

      {/* Drawer overlay */}
      {open && (
        <div className="fixed inset-0 z-50">
          {/* Backdrop */}
          <div className="absolute inset-0 bg-black/40" onClick={() => setOpen(false)} />

          {/* Mobile: full-height drawer above bottom nav */}
          <div
            className={`
              absolute bg-background flex flex-col
              md:left-auto md:right-0 md:top-0 md:bottom-0 md:w-80 md:border-l md:shadow-xl
              inset-x-0 bottom-16 top-0 rounded-b-none
              animate-in md:slide-in-from-right slide-in-from-bottom duration-200
            `}
          >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b shrink-0">
              <span className="font-semibold text-sm">
                Recent jobs
                {activeCount > 0 && (
                  <span className="ml-2 inline-flex items-center gap-1 text-xs font-normal text-muted-foreground">
                    <Loader2 size={12} className="animate-spin" />
                    {activeCount} active
                  </span>
                )}
              </span>
              <div className="flex items-center gap-1">
                {hasFinished && (
                  <button
                    onClick={handleClear}
                    title="Clear finished jobs"
                    className="p-1.5 rounded-md hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
                  >
                    <Trash2 size={16} />
                  </button>
                )}
                <button
                  onClick={() => setOpen(false)}
                  className="p-1.5 rounded-md hover:bg-muted transition-colors"
                >
                  <X size={18} />
                </button>
              </div>
            </div>

            {/* Job list */}
            <JobStatusPanel jobs={jobs} onRefresh={onRefresh} />
          </div>
        </div>
      )}
    </>
  );
}
