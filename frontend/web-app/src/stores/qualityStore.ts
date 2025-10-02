import { create } from 'zustand';

interface QualityMetrics {
  total_findings: number;
  validated_findings: number;
  false_positives: number;
  accuracy_rate: number;
  false_positive_rate: number;
  confidence_distribution: {
    high: number;
    medium: number;
    low: number;
  };
  validation_queue_size: number;
  calculated_at: string;
}

interface ValidationQueueItem {
  id: string;
  finding_type: string;
  finding_id: string;
  priority: string;
  status: string;
  assigned_to: string | null;
  created_at: string;
  reviewed_at: string | null;
  review_notes: string | null;
}

interface QualityStore {
  // State
  currentProjectId: string | null;
  metrics: QualityMetrics | null;
  queueItems: ValidationQueueItem[];
  selectedFinding: string | null;
  showValidationModal: boolean;
  filters: {
    priority: string | null;
    status: string | null;
    finding_type: string | null;
  };

  // Actions
  setCurrentProjectId: (projectId: string | null) => void;
  setMetrics: (metrics: QualityMetrics | null) => void;
  setQueueItems: (items: ValidationQueueItem[]) => void;
  setSelectedFinding: (findingId: string | null) => void;
  setShowValidationModal: (show: boolean) => void;
  setFilters: (filters: Partial<QualityStore['filters']>) => void;
  clearFilters: () => void;
  reset: () => void;
}

const initialState = {
  currentProjectId: null,
  metrics: null,
  queueItems: [],
  selectedFinding: null,
  showValidationModal: false,
  filters: {
    priority: null,
    status: null,
    finding_type: null,
  },
};

export const useQualityStore = create<QualityStore>((set) => ({
  ...initialState,

  setCurrentProjectId: (projectId: string | null) => set({ currentProjectId: projectId }),

  setMetrics: (metrics: QualityMetrics | null) => set({ metrics }),

  setQueueItems: (items: ValidationQueueItem[]) => set({ queueItems: items }),

  setSelectedFinding: (findingId: string | null) => set({ selectedFinding: findingId }),

  setShowValidationModal: (show: boolean) => set({ showValidationModal: show }),

  setFilters: (newFilters: Partial<QualityStore['filters']>) =>
    set((state) => ({
      filters: { ...state.filters, ...newFilters },
    })),

  clearFilters: () =>
    set({
      filters: {
        priority: null,
        status: null,
        finding_type: null,
      },
    }),

  reset: () => set(initialState),
}));
