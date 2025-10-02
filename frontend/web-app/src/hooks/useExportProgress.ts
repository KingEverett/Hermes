/**
 * useExportProgress Hook
 * Monitors export job progress with polling and optional WebSocket support
 */

import { useState, useEffect, useCallback } from 'react';

export interface ExportJob {
  id: string;
  project_id: string;
  format: 'svg' | 'png' | 'zip';
  status: 'pending' | 'processing' | 'completed' | 'failed';
  file_path?: string;
  download_url?: string;
  created_at: string;
  completed_at?: string;
  error_message?: string;
  progress?: number; // 0-100
  current_item?: number;
  total_items?: number;
}

export interface UseExportProgressOptions {
  jobId: string;
  projectId: string;
  pollInterval?: number; // milliseconds
  onComplete?: (job: ExportJob) => void;
  onError?: (error: string) => void;
  autoDownload?: boolean;
}

export interface UseExportProgressReturn {
  job: ExportJob | null;
  isLoading: boolean;
  isComplete: boolean;
  isFailed: boolean;
  progress: number;
  error: string | null;
  retry: () => void;
  cancel: () => void;
}

/**
 * Hook for monitoring export job progress
 */
export const useExportProgress = ({
  jobId,
  projectId,
  pollInterval = 1000,
  onComplete,
  onError,
  autoDownload = false
}: UseExportProgressOptions): UseExportProgressReturn => {
  const [job, setJob] = useState<ExportJob | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isCancelled, setIsCancelled] = useState(false);

  const fetchJobStatus = useCallback(async () => {
    if (isCancelled) return;

    try {
      const response = await fetch(
        `/api/v1/projects/${projectId}/exports/${jobId}`
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch export status: ${response.statusText}`);
      }

      const jobData: ExportJob = await response.json();
      setJob(jobData);
      setIsLoading(false);

      // Handle completion
      if (jobData.status === 'completed') {
        onComplete?.(jobData);

        // Auto-download if enabled
        if (autoDownload && jobData.download_url) {
          window.location.href = jobData.download_url;
        }
      }

      // Handle failure
      if (jobData.status === 'failed') {
        const errorMsg = jobData.error_message || 'Export failed';
        setError(errorMsg);
        onError?.(errorMsg);
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Unknown error';
      setError(errorMsg);
      setIsLoading(false);
      onError?.(errorMsg);
    }
  }, [jobId, projectId, isCancelled, onComplete, onError, autoDownload]);

  // Poll for status updates
  useEffect(() => {
    if (isCancelled) return;

    fetchJobStatus();

    // Continue polling if job is not complete or failed
    if (job?.status === 'pending' || job?.status === 'processing' || !job) {
      const intervalId = setInterval(fetchJobStatus, pollInterval);
      return () => clearInterval(intervalId);
    }
  }, [fetchJobStatus, job?.status, pollInterval, isCancelled]);

  const retry = useCallback(() => {
    setError(null);
    setIsLoading(true);
    setIsCancelled(false);
    fetchJobStatus();
  }, [fetchJobStatus]);

  const cancel = useCallback(() => {
    setIsCancelled(true);
    setIsLoading(false);
  }, []);

  const isComplete = job?.status === 'completed';
  const isFailed = job?.status === 'failed';
  const progress = job?.progress || 0;

  return {
    job,
    isLoading,
    isComplete,
    isFailed,
    progress,
    error,
    retry,
    cancel
  };
};

/**
 * Hook for batch export progress with multiple jobs
 */
export const useBatchExportProgress = (
  jobIds: string[],
  projectId: string
): {
  jobs: Record<string, ExportJob>;
  overallProgress: number;
  allComplete: boolean;
  anyFailed: boolean;
} => {
  const [jobs, setJobs] = useState<Record<string, ExportJob>>({});

  useEffect(() => {
    const fetchAllJobs = async () => {
      const promises = jobIds.map(async (jobId) => {
        const response = await fetch(
          `/api/v1/projects/${projectId}/exports/${jobId}`
        );
        const job: ExportJob = await response.json();
        return [jobId, job] as [string, ExportJob];
      });

      const results = await Promise.all(promises);
      const jobsMap = Object.fromEntries(results);
      setJobs(jobsMap);
    };

    if (jobIds.length > 0) {
      fetchAllJobs();
      const intervalId = setInterval(fetchAllJobs, 2000);
      return () => clearInterval(intervalId);
    }
  }, [jobIds, projectId]);

  const overallProgress = Object.values(jobs).reduce(
    (sum, job) => sum + (job.progress || 0),
    0
  ) / Math.max(jobIds.length, 1);

  const allComplete = jobIds.length > 0 && Object.values(jobs).every(
    job => job.status === 'completed'
  );

  const anyFailed = Object.values(jobs).some(
    job => job.status === 'failed'
  );

  return {
    jobs,
    overallProgress,
    allComplete,
    anyFailed
  };
};
