import { JobStatusChip } from "@/components/JobStatusChip";

interface JobStatusBarProps {
  jobIds: string[];
  onDismiss: (id: string) => void;
}

export function JobStatusBar({ jobIds, onDismiss }: JobStatusBarProps) {
  if (jobIds.length === 0) return null;

  return (
    <div className="fixed bottom-20 right-3 z-40 md:bottom-4 flex flex-col items-end gap-1.5 pointer-events-none">
      {jobIds.map((id) => (
        <div key={id} className="pointer-events-auto">
          <JobStatusChip jobId={id} onDismiss={() => onDismiss(id)} />
        </div>
      ))}
    </div>
  );
}
