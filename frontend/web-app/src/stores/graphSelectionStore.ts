/**
 * Graph Selection State Management
 *
 * Zustand store for managing node selection state in the network graph.
 * Supports single selection, multi-select, and hover states.
 */

import { create } from 'zustand';

interface GraphSelectionState {
  selectedNodeIds: string[];
  hoveredNodeId: string | null;

  selectNode: (nodeId: string) => void;
  toggleNode: (nodeId: string) => void;
  selectMultiple: (nodeIds: string[]) => void;
  selectAll: (allNodeIds: string[]) => void;
  clearSelection: () => void;
  setHoveredNode: (nodeId: string | null) => void;
}

export const useGraphSelectionStore = create<GraphSelectionState>((set) => ({
  selectedNodeIds: [],
  hoveredNodeId: null,

  selectNode: (nodeId: string) => set({ selectedNodeIds: [nodeId] }),

  toggleNode: (nodeId: string) => set((state) => ({
    selectedNodeIds: state.selectedNodeIds.includes(nodeId)
      ? state.selectedNodeIds.filter((id: string) => id !== nodeId)
      : [...state.selectedNodeIds, nodeId]
  })),

  selectMultiple: (nodeIds: string[]) => set({ selectedNodeIds: nodeIds }),

  selectAll: (allNodeIds: string[]) => set({ selectedNodeIds: allNodeIds }),

  clearSelection: () => set({ selectedNodeIds: [] }),

  setHoveredNode: (nodeId: string | null) => set({ hoveredNodeId: nodeId }),
}));
