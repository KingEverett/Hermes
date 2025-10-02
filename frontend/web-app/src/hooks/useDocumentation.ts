import {
  useQuery,
  useMutation,
  useQueryClient,
  QueryClient,
} from '@tanstack/react-query';
import {
  documentationApi,
  DocumentationSection,
  UpdateDocumentationRequest,
  AddNoteRequest,
  CreateDocumentationRequest,
} from '../services/documentationApi';

// Query keys
export const documentationKeys = {
  all: ['documentation'] as const,
  detail: (entityType: string, entityId: string) =>
    ['documentation', entityType, entityId] as const,
  versions: (docId: string) => ['documentation', 'versions', docId] as const,
};

/**
 * Hook for fetching documentation for a specific entity
 */
export const useDocumentation = (entityType: string, entityId: string) => {
  const queryClient = useQueryClient();

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: documentationKeys.detail(entityType, entityId),
    queryFn: () => documentationApi.getDocumentation(entityType, entityId),
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 2,
  });

  const updateMutation = useMutation({
    mutationFn: (updateData: UpdateDocumentationRequest) =>
      documentationApi.updateDocumentation(entityType, entityId, updateData),
    onMutate: async (newData: UpdateDocumentationRequest) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({
        queryKey: documentationKeys.detail(entityType, entityId),
      });

      // Snapshot previous value
      const previousData = queryClient.getQueryData<DocumentationSection>(
        documentationKeys.detail(entityType, entityId)
      );

      // Optimistically update
      if (previousData) {
        queryClient.setQueryData<DocumentationSection>(
          documentationKeys.detail(entityType, entityId),
          {
            ...previousData,
            content: newData.content,
            source_type: newData.source_type || previousData.source_type,
            updated_at: new Date().toISOString(),
          }
        );
      }

      return { previousData };
    },
    onError: (err: any, variables: UpdateDocumentationRequest, context: any) => {
      // Rollback on error
      if (context?.previousData) {
        queryClient.setQueryData(
          documentationKeys.detail(entityType, entityId),
          context.previousData
        );
      }
    },
    onSuccess: () => {
      // Invalidate and refetch
      queryClient.invalidateQueries({
        queryKey: documentationKeys.all,
      });
    },
  });

  const addNoteMutation = useMutation({
    mutationFn: (noteData: AddNoteRequest) =>
      documentationApi.addNote(entityType, entityId, noteData),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: documentationKeys.detail(entityType, entityId),
      });
    },
  });

  return {
    documentation: data,
    isLoading,
    error,
    refetch,
    updateDocumentation: updateMutation.mutate,
    updateDocumentationAsync: updateMutation.mutateAsync,
    isUpdating: updateMutation.isPending,
    addNote: addNoteMutation.mutate,
    addNoteAsync: addNoteMutation.mutateAsync,
    isAddingNote: addNoteMutation.isPending,
  };
};

/**
 * Hook for creating new documentation
 */
export const useCreateDocumentation = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateDocumentationRequest) =>
      documentationApi.createDocumentation(data),
    onSuccess: (data: DocumentationSection) => {
      queryClient.invalidateQueries({
        queryKey: documentationKeys.detail(data.entity_type, data.entity_id),
      });
    },
  });
};

/**
 * Hook for fetching version history
 */
export const useVersionHistory = (docId: string | undefined) => {
  return useQuery({
    queryKey: documentationKeys.versions(docId || ''),
    queryFn: () => documentationApi.getVersionHistory(docId!),
    enabled: !!docId,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
};

/**
 * Hook for rolling back to a previous version
 */
export const useRollback = (docId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (versionId: string) =>
      documentationApi.rollbackToVersion(docId, versionId),
    onSuccess: (data: DocumentationSection) => {
      // Invalidate the documentation and version history
      queryClient.invalidateQueries({
        queryKey: documentationKeys.detail(data.entity_type, data.entity_id),
      });
      queryClient.invalidateQueries({
        queryKey: documentationKeys.versions(docId),
      });
    },
  });
};

export default useDocumentation;
