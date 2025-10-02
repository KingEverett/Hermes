import {
  useQuery,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query';
import {
  documentationApi,
  CreateTemplateRequest,
} from '../services/documentationApi';

// Query keys
export const templateKeys = {
  all: ['templates'] as const,
  list: (category?: string) => ['templates', { category }] as const,
  detail: (id: string) => ['templates', id] as const,
};

/**
 * Hook for fetching templates with optional category filter
 */
export const useTemplates = (category?: string) => {
  return useQuery({
    queryKey: templateKeys.list(category),
    queryFn: () => documentationApi.getTemplates(category),
    staleTime: 10 * 60 * 1000, // 10 minutes (templates change infrequently)
  });
};

/**
 * Hook for fetching a single template
 */
export const useTemplate = (id: string | undefined) => {
  return useQuery({
    queryKey: templateKeys.detail(id || ''),
    queryFn: () => documentationApi.getTemplate(id!),
    enabled: !!id,
    staleTime: 10 * 60 * 1000,
  });
};

/**
 * Hook for creating a new template
 */
export const useCreateTemplate = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateTemplateRequest) =>
      documentationApi.createTemplate(data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: templateKeys.all,
      });
    },
  });
};

/**
 * Hook for updating a template
 */
export const useUpdateTemplate = (id: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: Partial<CreateTemplateRequest>) =>
      documentationApi.updateTemplate(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: templateKeys.detail(id),
      });
      queryClient.invalidateQueries({
        queryKey: templateKeys.all,
      });
    },
  });
};

/**
 * Hook for deleting a template
 */
export const useDeleteTemplate = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => documentationApi.deleteTemplate(id),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: templateKeys.all,
      });
    },
  });
};

export default useTemplates;
