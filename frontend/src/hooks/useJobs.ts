import { useCallback, useEffect, useRef, useState } from "react";
import { fetchJobs } from "@/api/client";
import type { JobStatus } from "@/types";

const POLL_ACTIVE = 1500;
const POLL_IDLE = 10000;
const TERMINAL = new Set(["done", "error", "skipped"]);

function hasActiveJobs(jobs: Record<string, JobStatus>): boolean {
  return Object.values(jobs).some((j) => !TERMINAL.has(j.status));
}

export function useJobs() {
  const [jobs, setJobs] = useState<Record<string, JobStatus>>({});
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);

  const poll = useCallback(async () => {
    try {
      const data = await fetchJobs();
      if (!mountedRef.current) return;
      setJobs(data);
      // Schedule next poll based on current state
      const delay = hasActiveJobs(data) ? POLL_ACTIVE : POLL_IDLE;
      timerRef.current = setTimeout(poll, delay);
    } catch {
      // Retry after idle interval on error
      if (mountedRef.current) {
        timerRef.current = setTimeout(poll, POLL_IDLE);
      }
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    poll();
    return () => {
      mountedRef.current = false;
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [poll]);

  const refresh = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    poll();
  }, [poll]);

  return { jobs, refresh };
}
