import { useEffect } from "react";
import { Link } from "react-router-dom";
import { useSSE } from "@/hooks/useSSE";

const STATUS_LABELS: Record<string, string> = {
  queued: "Queued",
  processing: "Processing",
  enhancing: "Enhancing",
  extracting: "Extracting",
  saving: "Saving",
};

interface JobStatusChipProps {
  jobId: string;
  onDismiss: () => void;
}

export function JobStatusChip({ jobId, onDismiss }: JobStatusChipProps) {
  const status = useSSE(jobId);

  const isDone = status?.status === "done";
  const isError = status?.status === "error";
  const isSkipped = status?.status === "skipped";

  useEffect(() => {
    if (!isDone) return;
    const timer = setTimeout(onDismiss, 10000);
    return () => clearTimeout(timer);
  }, [isDone, onDismiss]);

  return (
    <div
      className={`flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium border ${
        isDone
          ? "bg-green-50 border-green-200 text-green-800"
          : isSkipped
          ? "bg-amber-50 border-amber-200 text-amber-800"
          : isError
          ? "bg-red-50 border-red-200 text-red-800"
          : "bg-muted border-border text-muted-foreground"
      }`}
    >
      {!isDone && !isError && !isSkipped && (
        <div className="h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" />
      )}

      {isDone && status.letter_id ? (
        <Link
          to={`/letters/${status.letter_id}`}
          className="underline underline-offset-2 hover:no-underline"
        >
          Letter ready
        </Link>
      ) : isDone ? (
        <span>Letter ready</span>
      ) : isSkipped && status.duplicate_of ? (
        <Link
          to={`/letters/${status.duplicate_of}`}
          className="underline underline-offset-2 hover:no-underline"
        >
          Skipped — duplicate of #{status.duplicate_of}
        </Link>
      ) : isSkipped ? (
        <span>Skipped — duplicate</span>
      ) : isError ? (
        <span title={status.error ?? undefined}>Failed</span>
      ) : (
        <span>{STATUS_LABELS[status?.status ?? ""] ?? "Uploading..."}</span>
      )}

      <button
        onClick={onDismiss}
        aria-label="Dismiss"
        className="ml-0.5 flex h-3.5 w-3.5 items-center justify-center rounded-full hover:bg-black/10 text-xs leading-none"
      >
        ×
      </button>
    </div>
  );
}
