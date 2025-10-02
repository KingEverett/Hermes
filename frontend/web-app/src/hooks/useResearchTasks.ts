import { useQuery } from '@tanstack/react-query';

interface ResearchTask {
  id: string;
  project_id: string;
  target_type: 'service' | 'vulnerability' | 'host';
  target_id: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  source: 'nvd' | 'exploitdb' | 'cisa' | 'manual';
  results?: any;
  error_message?: string;
  retry_count: number;
  created_at: Date | string;
  completed_at?: Date | string;
}

const fetchResearchTasks = async (targetId: string, targetType: string): Promise<ResearchTask[]> => {
  const response = await fetch(`/api/v1/research/tasks?target_id=${targetId}&target_type=${targetType}`);

  if (!response.ok) {
    if (response.status === 404) {
      return []; // Return empty array if no tasks found
    }
    throw new Error('Failed to fetch research tasks');
  }

  return response.json();
};

export const useResearchTasks = (targetId: string | undefined, targetType: 'host' | 'service' | 'vulnerability') => {
  return useQuery({
    queryKey: ['research', 'tasks', targetType, targetId],
    queryFn: () => fetchResearchTasks(targetId!, targetType),
    enabled: !!targetId,
    staleTime: 10000, // 10 seconds (more frequent updates for task status)
    refetchOnWindowFocus: true,
    refetchInterval: 15000, // Poll every 15 seconds for task status updates
  });
};
