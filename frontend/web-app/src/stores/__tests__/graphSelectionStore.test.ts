/**
 * graphSelectionStore Tests
 *
 * Test suite for Zustand graph selection state management.
 */

import { renderHook, act } from '@testing-library/react';
import { useGraphSelectionStore } from '../graphSelectionStore';

describe('graphSelectionStore', () => {
  beforeEach(() => {
    // Reset store to initial state before each test
    const { result } = renderHook(() => useGraphSelectionStore());
    act(() => {
      result.current.clearSelection();
      result.current.setHoveredNode(null);
    });
  });

  describe('Initial State', () => {
    test('starts with empty selection', () => {
      const { result } = renderHook(() => useGraphSelectionStore());

      expect(result.current.selectedNodeIds).toEqual([]);
    });

    test('starts with no hovered node', () => {
      const { result } = renderHook(() => useGraphSelectionStore());

      expect(result.current.hoveredNodeId).toBeNull();
    });
  });

  describe('selectNode', () => {
    test('selects a single node', () => {
      const { result } = renderHook(() => useGraphSelectionStore());

      act(() => {
        result.current.selectNode('node1');
      });

      expect(result.current.selectedNodeIds).toEqual(['node1']);
    });

    test('replaces previous selection', () => {
      const { result } = renderHook(() => useGraphSelectionStore());

      act(() => {
        result.current.selectNode('node1');
      });

      act(() => {
        result.current.selectNode('node2');
      });

      expect(result.current.selectedNodeIds).toEqual(['node2']);
    });
  });

  describe('toggleNode', () => {
    test('adds node to selection if not present', () => {
      const { result } = renderHook(() => useGraphSelectionStore());

      act(() => {
        result.current.toggleNode('node1');
      });

      expect(result.current.selectedNodeIds).toEqual(['node1']);
    });

    test('removes node from selection if present', () => {
      const { result } = renderHook(() => useGraphSelectionStore());

      act(() => {
        result.current.selectNode('node1');
        result.current.toggleNode('node1');
      });

      expect(result.current.selectedNodeIds).toEqual([]);
    });

    test('adds to existing selection', () => {
      const { result } = renderHook(() => useGraphSelectionStore());

      act(() => {
        result.current.selectNode('node1');
        result.current.toggleNode('node2');
      });

      expect(result.current.selectedNodeIds).toContain('node1');
      expect(result.current.selectedNodeIds).toContain('node2');
      expect(result.current.selectedNodeIds).toHaveLength(2);
    });

    test('removes specific node from multi-selection', () => {
      const { result } = renderHook(() => useGraphSelectionStore());

      act(() => {
        result.current.selectMultiple(['node1', 'node2', 'node3']);
        result.current.toggleNode('node2');
      });

      expect(result.current.selectedNodeIds).toEqual(['node1', 'node3']);
    });
  });

  describe('selectMultiple', () => {
    test('selects multiple nodes', () => {
      const { result } = renderHook(() => useGraphSelectionStore());

      act(() => {
        result.current.selectMultiple(['node1', 'node2', 'node3']);
      });

      expect(result.current.selectedNodeIds).toEqual(['node1', 'node2', 'node3']);
    });

    test('replaces previous selection with new array', () => {
      const { result } = renderHook(() => useGraphSelectionStore());

      act(() => {
        result.current.selectMultiple(['node1', 'node2']);
      });

      act(() => {
        result.current.selectMultiple(['node3', 'node4']);
      });

      expect(result.current.selectedNodeIds).toEqual(['node3', 'node4']);
    });

    test('handles empty array', () => {
      const { result } = renderHook(() => useGraphSelectionStore());

      act(() => {
        result.current.selectNode('node1');
        result.current.selectMultiple([]);
      });

      expect(result.current.selectedNodeIds).toEqual([]);
    });
  });

  describe('selectAll', () => {
    test('selects all provided nodes', () => {
      const { result } = renderHook(() => useGraphSelectionStore());
      const allNodes = ['node1', 'node2', 'node3', 'node4', 'node5'];

      act(() => {
        result.current.selectAll(allNodes);
      });

      expect(result.current.selectedNodeIds).toEqual(allNodes);
    });

    test('replaces previous selection', () => {
      const { result } = renderHook(() => useGraphSelectionStore());

      act(() => {
        result.current.selectNode('node1');
        result.current.selectAll(['node2', 'node3', 'node4']);
      });

      expect(result.current.selectedNodeIds).toEqual(['node2', 'node3', 'node4']);
    });
  });

  describe('clearSelection', () => {
    test('clears single selection', () => {
      const { result } = renderHook(() => useGraphSelectionStore());

      act(() => {
        result.current.selectNode('node1');
        result.current.clearSelection();
      });

      expect(result.current.selectedNodeIds).toEqual([]);
    });

    test('clears multiple selection', () => {
      const { result } = renderHook(() => useGraphSelectionStore());

      act(() => {
        result.current.selectMultiple(['node1', 'node2', 'node3']);
        result.current.clearSelection();
      });

      expect(result.current.selectedNodeIds).toEqual([]);
    });

    test('does nothing if already empty', () => {
      const { result } = renderHook(() => useGraphSelectionStore());

      act(() => {
        result.current.clearSelection();
      });

      expect(result.current.selectedNodeIds).toEqual([]);
    });
  });

  describe('setHoveredNode', () => {
    test('sets hovered node', () => {
      const { result } = renderHook(() => useGraphSelectionStore());

      act(() => {
        result.current.setHoveredNode('node1');
      });

      expect(result.current.hoveredNodeId).toBe('node1');
    });

    test('changes hovered node', () => {
      const { result } = renderHook(() => useGraphSelectionStore());

      act(() => {
        result.current.setHoveredNode('node1');
        result.current.setHoveredNode('node2');
      });

      expect(result.current.hoveredNodeId).toBe('node2');
    });

    test('clears hovered node with null', () => {
      const { result } = renderHook(() => useGraphSelectionStore());

      act(() => {
        result.current.setHoveredNode('node1');
        result.current.setHoveredNode(null);
      });

      expect(result.current.hoveredNodeId).toBeNull();
    });
  });

  describe('Complex Interaction Scenarios', () => {
    test('hover does not affect selection', () => {
      const { result } = renderHook(() => useGraphSelectionStore());

      act(() => {
        result.current.selectNode('node1');
        result.current.setHoveredNode('node2');
      });

      expect(result.current.selectedNodeIds).toEqual(['node1']);
      expect(result.current.hoveredNodeId).toBe('node2');
    });

    test('selection does not affect hover', () => {
      const { result } = renderHook(() => useGraphSelectionStore());

      act(() => {
        result.current.setHoveredNode('node1');
        result.current.selectNode('node2');
      });

      expect(result.current.hoveredNodeId).toBe('node1');
      expect(result.current.selectedNodeIds).toEqual(['node2']);
    });

    test('can hover and select same node', () => {
      const { result } = renderHook(() => useGraphSelectionStore());

      act(() => {
        result.current.selectNode('node1');
        result.current.setHoveredNode('node1');
      });

      expect(result.current.selectedNodeIds).toEqual(['node1']);
      expect(result.current.hoveredNodeId).toBe('node1');
    });

    test('complex multi-select workflow', () => {
      const { result } = renderHook(() => useGraphSelectionStore());

      // Select first node
      act(() => {
        result.current.selectNode('node1');
      });
      expect(result.current.selectedNodeIds).toEqual(['node1']);

      // Add second node via toggle
      act(() => {
        result.current.toggleNode('node2');
      });
      expect(result.current.selectedNodeIds).toHaveLength(2);

      // Add third node via toggle
      act(() => {
        result.current.toggleNode('node3');
      });
      expect(result.current.selectedNodeIds).toHaveLength(3);

      // Remove middle node
      act(() => {
        result.current.toggleNode('node2');
      });
      expect(result.current.selectedNodeIds).toEqual(['node1', 'node3']);

      // Clear all
      act(() => {
        result.current.clearSelection();
      });
      expect(result.current.selectedNodeIds).toEqual([]);
    });
  });

  describe('Store Persistence', () => {
    test('maintains state across multiple hook instances', () => {
      const { result: result1 } = renderHook(() => useGraphSelectionStore());

      act(() => {
        result1.current.selectNode('node1');
      });

      const { result: result2 } = renderHook(() => useGraphSelectionStore());

      expect(result2.current.selectedNodeIds).toEqual(['node1']);
    });

    test('updates propagate to all hook instances', () => {
      const { result: result1 } = renderHook(() => useGraphSelectionStore());
      const { result: result2 } = renderHook(() => useGraphSelectionStore());

      act(() => {
        result1.current.selectNode('node1');
      });

      expect(result2.current.selectedNodeIds).toEqual(['node1']);

      act(() => {
        result2.current.toggleNode('node2');
      });

      expect(result1.current.selectedNodeIds).toContain('node1');
      expect(result1.current.selectedNodeIds).toContain('node2');
    });
  });
});
