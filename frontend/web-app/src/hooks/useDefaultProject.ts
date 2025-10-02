/**
 * useDefaultProject hook
 *
 * Fetches the default/first project from the API for initial app load.
 */

import { useQuery } from '@tanstack/react-query';

interface Project {
  id: string;
  name: string;
  description?: string;
  created_at: string;
}

const fetchProjects = async (): Promise<Project[]> => {
  const response = await fetch('/api/v1/projects/');

  if (!response.ok) {
    throw new Error(`Failed to fetch projects: ${response.statusText}`);
  }

  return response.json();
};

export const useDefaultProject = () => {
  const { data, isLoading, error, refetch } = useQuery<Project[], Error>({
    queryKey: ['projects'],
    queryFn: fetchProjects,
  });

  // Get first project as default
  const defaultProject = data?.[0] || null;
  const hasProjects = (data?.length ?? 0) > 0;

  return {
    project: defaultProject,
    hasProjects,
    isLoading,
    error,
    refetch,
  };
};
