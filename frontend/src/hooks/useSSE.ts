import { useEffect, useRef, useState } from "react";
import type { IngestStatus } from "@/types";

export function useSSE(jobId: string | null) {
  const [status, setStatus] = useState<IngestStatus | null>(null);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!jobId) return;

    const es = new EventSource(`/api/letters/ingest/${jobId}/status`);
    esRef.current = es;

    es.onmessage = (event) => {
      const data: IngestStatus = JSON.parse(event.data);
      setStatus(data);
      if (data.status === "done" || data.status === "error" || data.status === "skipped") {
        es.close();
      }
    };

    es.onerror = () => {
      es.close();
    };

    return () => {
      es.close();
    };
  }, [jobId]);

  return status;
}
