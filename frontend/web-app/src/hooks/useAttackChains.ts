/**
 * React Query hooks for Attack Chain data fetching and mutations
 */

import {
  useQuery,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query';
import type {
  AttackChain,
  AttackChainListItem,
  AttackChainCreate,
  AttackChainUpdate,
} from '../types/attackChain';
import * as attackChainApi from '../services/attackChainApi';

// Query keys
export const attackChainKeys = {
  all: ['attack-chains'] as const,
  lists: () => [...attackChainKeys.all, 'list'] as const,
  list: (projectId: string) => [...attackChainKeys.lists(), projectId] as const,
  details: () => [...attackChainKeys.all, 'detail'] as const,
  detail: (chainId: string) => [...attackChainKeys.details(), chainId] as const,
};

/**
 * Hook for fetching all attack chains for a project
 */
export const useProjectAttackChains = (projectId: string) => {
  return useQuery({
    queryKey: attackChainKeys.list(projectId),
    queryFn: () => attackChainApi.getProjectAttackChains(projectId),
    staleTime: 5 * 60 * 1000, // 5 minutes
    enabled: !!projectId,
  });
};

/**
 * Hook for fetching a single attack chain with nodes
 */
export const useAttackChain = (chainId: string) => {
  return useQuery({
    queryKey: attackChainKeys.detail(chainId),
    queryFn: () => attackChainApi.getAttackChain(chainId),
    staleTime: 5 * 60 * 1000,
    enabled: !!chainId,
  });
};

/**
 * Hook for creating a new attack chain
 */
export const useCreateAttackChain = (projectId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: AttackChainCreate) =>
      attackChainApi.createAttackChain(projectId, data),
    onSuccess: (newChain: AttackChain) => {
      // Invalidate the project's chain list to refetch
      queryClient.invalidateQueries({
        queryKey: attackChainKeys.list(projectId),
      });

      // Add the new chain to the cache
      queryClient.setQueryData(
        attackChainKeys.detail(newChain.id),
        newChain
      );
    },
  });
};

/**
 * Hook for updating an existing attack chain
 */
export const useUpdateAttackChain = (chainId: string, projectId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: AttackChainUpdate) =>
      attackChainApi.updateAttackChain(chainId, data),
    onMutate: async (newData: AttackChainUpdate) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({
        queryKey: attackChainKeys.detail(chainId),
      });

      // Snapshot previous value
      const previousChain = queryClient.getQueryData<AttackChain>(
        attackChainKeys.detail(chainId)
      );

      // Optimistically update
      if (previousChain) {
        const updatedChain: AttackChain = {
          ...previousChain,
          ...newData,
          updated_at: new Date(),
          // Keep existing nodes if not updating them
          nodes: newData.nodes ? previousChain.nodes : previousChain.nodes,
        };
        queryClient.setQueryData<AttackChain>(
          attackChainKeys.detail(chainId),
          updatedChain
        );
      }

      return { previousChain };
    },
    onError: (err: any, newData: AttackChainUpdate, context: any) => {
      // Rollback on error
      if (context?.previousChain) {
        queryClient.setQueryData(
          attackChainKeys.detail(chainId),
          context.previousChain
        );
      }
    },
    onSuccess: () => {
      // Invalidate to ensure fresh data
      queryClient.invalidateQueries({
        queryKey: attackChainKeys.detail(chainId),
      });
      queryClient.invalidateQueries({
        queryKey: attackChainKeys.list(projectId),
      });
    },
  });
};

/**
 * Hook for deleting an attack chain
 */
export const useDeleteAttackChain = (projectId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (chainId: string) => attackChainApi.deleteAttackChain(chainId),
    onSuccess: (_: any, chainId: string) => {
      // Remove from cache
      queryClient.removeQueries({
        queryKey: attackChainKeys.detail(chainId),
      });

      // Invalidate list to refetch
      queryClient.invalidateQueries({
        queryKey: attackChainKeys.list(projectId),
      });
    },
  });
};
