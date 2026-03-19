import { useState } from "react";
import { Link } from "react-router-dom";
import { forceIngest } from "@/api/client";
import type { JobStatus } from "@/types";
import { CheckCircle2, AlertCircle, Copy, Loader2 } from "lucide-react";

const STATUS_LABELS: Record<string, string> = {
  queued: "Queued",
  enhancing: "Enhancing",
  extracting: "Extracting",
  saving: "Saving",
};

const TERMINAL = new Set(["done", "error", "skipped"]);

function timeAgo(ts: number): string {
  const seconds = Math.floor(Date.now() / 1000 - ts);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  return `${minutes}m ago`;
}

interface JobRowProps {
  jobId: string;
  job: JobStatus;
  onForced: () => void;
  onNavigate?: () => void;
}

function JobRow({ jobId, job, onForced, onNavigate }: JobRowProps) {
  const [forcing, setForcing] = useState(false);
  const [forceError, setForceError] = useState<string | null>(null);

  const isDone = job.status === "done";
  const isError = job.status === "error";
  const isSkipped = job.status === "skipped";
  const isActive = !TERMINAL.has(job.status);

  async function handleForce() {
    setForcing(true);
    setForceError(null);
    try {
      await forceIngest(jobId);
      onForced();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setForceError(msg.startsWith("410") ? "Expired — re-upload" : "Force failed");
    } finally {
      setForcing(false);
    }
  }

  return (
    <div className="flex items-center gap-3 py-3 px-4 text-sm">
      {/* Icon */}
      <div className="shrink-0">
        {isActive && <Loader2 size={16} className="animate-spin text-muted-foreground" />}
        {isDone && <CheckCircle2 size={16} className="text-green-600" />}
        {isError && <AlertCircle size={16} className="text-red-500" />}
        {isSkipped && <Copy size={16} className="text-amber-500" />}
      </div>

      {/* Label */}
      <div className="flex-1 min-w-0">
        {isDone && job.letter_id ? (
          <Link
            to={`/letters/${job.letter_id}`}
            onClick={onNavigate}
            className="text-green-700 underline underline-offset-2 hover:no-underline"
          >
            Letter #{job.letter_id} ready
          </Link>
        ) : isDone ? (
          <span className="text-green-700">Done</span>
        ) : isSkipped && forceError ? (
          <span className="text-amber-700">{forceError}</span>
        ) : isSkipped && job.duplicate_of ? (
          <span className="text-amber-700">
            Duplicate of{" "}
            <Link
              to={`/letters/${job.duplicate_of}`}
              onClick={onNavigate}
              className="underline underline-offset-2 hover:no-underline"
            >
              #{job.duplicate_of}
            </Link>
            {" · "}
            <button
              onClick={handleForce}
              disabled={forcing}
              className="underline underline-offset-2 hover:no-underline disabled:opacity-50"
            >
              {forcing ? "..." : "Ingest anyway"}
            </button>
          </span>
        ) : isError ? (
          <span className="text-red-600 truncate block" title={job.error ?? undefined}>
            Failed{job.error ? `: ${job.error.split(":")[0]}` : ""}
          </span>
        ) : (
          <span className="text-muted-foreground">
            {STATUS_LABELS[job.status] ?? job.status}
          </span>
        )}
      </div>

      {/* Timestamp */}
      <span className="text-xs text-muted-foreground shrink-0">{timeAgo(job.created_at)}</span>
    </div>
  );
}

interface JobStatusPanelProps {
  jobs: Record<string, JobStatus>;
  onRefresh: () => void;
  onNavigate?: () => void;
}

export function JobStatusPanel({ jobs, onRefresh, onNavigate }: JobStatusPanelProps) {
  const entries = Object.entries(jobs).sort(([, a], [, b]) => b.created_at - a.created_at);

  if (entries.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-sm text-muted-foreground py-12">
        No recent jobs
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto divide-y">
      {entries.map(([jid, job]) => (
        <JobRow key={jid} jobId={jid} job={job} onForced={onRefresh} onNavigate={onNavigate} />
      ))}
    </div>
  );
}
