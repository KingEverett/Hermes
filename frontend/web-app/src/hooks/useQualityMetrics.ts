import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  qualityApi,
  ValidationDecisionRequest,
  ValidationFeedbackRequest,
} from '../services/qualityApi';

export const useQualityMetrics = (projectId: string | null) => {
  return useQuery({
    queryKey: ['quality-metrics', projectId],
    queryFn: () => qualityApi.getQualityMetrics(projectId!),
    enabled: !!projectId,
    refetchInterval: 60000, // Refetch every minute
  });
};

export const useQualityTrends = (
  projectId: string | null,
  days: number = 30
) => {
  return useQuery({
    queryKey: ['quality-trends', projectId, days],
    queryFn: () => qualityApi.getQualityTrends(projectId!, { days }),
    enabled: !!projectId,
  });
};

export const useValidationQueue = (filters?: {
  priority?: string;
  status?: string;
  finding_type?: string;
}) => {
  return useQuery({
    queryKey: ['validation-queue', filters],
    queryFn: () => qualityApi.getValidationQueue(filters),
    refetchInterval: 30000, // Refetch every 30 seconds
  });
};

export const useValidationHistory = (findingId: string | null) => {
  return useQuery({
    queryKey: ['validation-history', findingId],
    queryFn: () => qualityApi.getValidationHistory(findingId!),
    enabled: !!findingId,
  });
};

export const useAccuracyIssues = (projectId: string | null) => {
  return useQuery({
    queryKey: ['accuracy-issues', projectId],
    queryFn: () => qualityApi.getAccuracyIssues(projectId!),
    enabled: !!projectId,
  });
};

export const useCoverageMetrics = (projectId: string | null) => {
  return useQuery({
    queryKey: ['coverage-metrics', projectId],
    queryFn: () => qualityApi.getCoverageMetrics(projectId!),
    enabled: !!projectId,
  });
};

export const useSubmitValidationReview = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      findingId,
      request,
    }: {
      findingId: string;
      request: ValidationDecisionRequest;
    }) => qualityApi.submitValidationReview(findingId, request),
    onSuccess: () => {
      // Invalidate validation queue and metrics to refresh data
      queryClient.invalidateQueries({ queryKey: ['validation-queue'] });
      queryClient.invalidateQueries({ queryKey: ['quality-metrics'] });
      queryClient.invalidateQueries({ queryKey: ['validation-history'] });
    },
  });
};

export const useSubmitFeedback = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: ValidationFeedbackRequest) =>
      qualityApi.submitFeedback(request),
    onSuccess: () => {
      // Invalidate metrics to reflect feedback
      queryClient.invalidateQueries({ queryKey: ['quality-metrics'] });
    },
  });
};

export const useRefreshVulnerability = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (vulnId: string) => qualityApi.refreshVulnerability(vulnId),
    onSuccess: () => {
      // Invalidate relevant queries
      queryClient.invalidateQueries({ queryKey: ['quality-metrics'] });
    },
  });
};
