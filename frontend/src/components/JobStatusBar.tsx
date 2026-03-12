import { JobStatusChip } from "@/components/JobStatusChip";

const MAX_VISIBLE = 3;

interface JobStatusBarProps {
  jobIds: string[];
  onDismiss: (id: string) => void;
  onForceJob: (newJobId: string) => void;
}

export function JobStatusBar({ jobIds, onDismiss, onForceJob }: JobStatusBarProps) {
  if (jobIds.length === 0) return null;

  const hidden = jobIds.length - MAX_VISIBLE;
  const visibleIds = new Set(jobIds.slice(-MAX_VISIBLE));

  return (
    <div className="fixed top-3 right-3 z-40 flex flex-col items-end gap-1.5 pointer-events-none">
      {hidden > 0 && (
        <div className="pointer-events-auto rounded-full px-3 py-1 text-xs font-medium bg-muted border border-border text-muted-foreground">
          +{hidden} more running
        </div>
      )}
      {jobIds.map((id) => (
        <div key={id} className="pointer-events-auto" style={visibleIds.has(id) ? undefined : { display: "none" }}>
          <JobStatusChip jobId={id} onDismiss={() => onDismiss(id)} onForceJob={onForceJob} />
        </div>
      ))}
    </div>
  );
}
