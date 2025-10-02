/**
 * useNetworkData hook
 *
 * React Query hook for fetching network topology data from the API.
 * Provides automatic caching, refetching, and state management.
 */

import { useQuery, UseQueryResult } from '@tanstack/react-query';

// Type definitions matching backend models
interface GraphNode {
  id: string;
  type: 'host' | 'service';
  label: string;
  x: number;
  y: number;
  metadata: {
    os?: string;
    hostname?: string;
    status?: string;
    service_name?: string;
    product?: string;
    version?: string;
    vuln_count?: number;
    max_severity?: string;
    has_exploit?: boolean;
    color?: string;
  };
}

interface GraphEdge {
  source: string;
  target: string;
}

export interface NetworkTopology {
  nodes: GraphNode[];
  edges: GraphEdge[];
  metadata: {
    node_count: number;
    edge_count: number;
    generated_at: string;
    layout_algorithm?: string;
  };
}

/**
 * Fetch network topology data from the API.
 *
 * @param projectId - UUID of the project
 * @returns Promise resolving to NetworkTopology data
 */
async function fetchNetworkTopology(projectId: string): Promise<NetworkTopology> {
  const response = await fetch(`/api/v1/projects/${projectId}/topology`);

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.detail || `Failed to fetch topology: ${response.statusText}`
    );
  }

  return response.json();
}

/**
 * React Query hook for fetching and managing network topology data.
 *
 * Features:
 * - Automatic caching with 5-minute stale time
 * - Automatic refetch on project change
 * - Loading and error state management
 * - Background refetching on window focus
 *
 * @param projectId - UUID of the project to fetch topology for
 * @returns UseQueryResult with topology data and query state
 *
 * @example
 * ```tsx
 * function TopologyView({ projectId }: { projectId: string }) {
 *   const { data, isLoading, error } = useNetworkData(projectId);
 *
 *   if (isLoading) return <div>Loading...</div>;
 *   if (error) return <div>Error: {error.message}</div>;
 *   if (!data) return <div>No data</div>;
 *
 *   return <NetworkGraph topology={data} />;
 * }
 * ```
 */
export function useNetworkData(
  projectId: string | undefined
): UseQueryResult<NetworkTopology, Error> {
  return useQuery<NetworkTopology, Error>({
    queryKey: ['networkTopology', projectId],
    queryFn: () => {
      if (!projectId) {
        throw new Error('Project ID is required');
      }
      return fetchNetworkTopology(projectId);
    },
    enabled: !!projectId, // Only run query if projectId is provided
    staleTime: 5 * 60 * 1000, // 5 minutes - matches backend cache TTL
    gcTime: 10 * 60 * 1000, // 10 minutes garbage collection time
    refetchOnWindowFocus: true,
    retry: 2,
    retryDelay: (attemptIndex: number) => Math.min(1000 * 2 ** attemptIndex, 30000)
  });
}
