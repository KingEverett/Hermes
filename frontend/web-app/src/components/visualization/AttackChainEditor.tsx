/**
 * Attack Chain Editor Modal
 *
 * Modal for editing existing attack chains with drag-and-drop reordering,
 * node addition/removal, and real-time preview
 */

import React, { useState, useEffect } from 'react';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { useAttackChain, useUpdateAttackChain } from '../../hooks/useAttackChains';
import type { AttackChain, AttackChainNode, AttackChainNodeCreate } from '../../types/attackChain';

interface AttackChainEditorProps {
  chainId: string;
  projectId: string;
  isOpen: boolean;
  onClose: () => void;
  onSave?: (chain: AttackChain) => void;
  onNodeSelect?: (callback: (nodeId: string) => void) => void;
}

interface EditableNode extends AttackChainNodeCreate {
  id: string; // Temp ID for key management during editing
}

interface SortableNodeItemProps {
  node: EditableNode;
  index: number;
  onRemove: (id: string) => void;
  onUpdate: (id: string, updates: Partial<EditableNode>) => void;
  expandedIds: Set<string>;
  onToggleExpand: (id: string) => void;
}

const SortableNodeItem: React.FC<SortableNodeItemProps> = ({
  node,
  index,
  onRemove,
  onUpdate,
  expandedIds,
  onToggleExpand,
}) => {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: node.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  const isExpanded = expandedIds.has(node.id);

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="bg-gray-700 rounded border border-gray-600 mb-2"
    >
      <div className="flex items-center p-3">
        {/* Drag Handle */}
        <div
          {...attributes}
          {...listeners}
          className="text-gray-400 hover:text-gray-200 cursor-grab active:cursor-grabbing mr-3 text-lg"
        >
          ☰
        </div>

        {/* Sequence Number */}
        <span className="text-gray-300 font-mono text-sm mr-3 min-w-[2rem]">
          {index + 1}.
        </span>

        {/* Entity Info */}
        <div className="flex-1 text-gray-100 text-sm">
          <span className="font-medium">{node.entity_type}</span>
          <span className="text-gray-400 ml-2">
            {node.entity_id.substring(0, 8)}...
          </span>
        </div>

        {/* Expand/Collapse Button */}
        <button
          onClick={() => onToggleExpand(node.id)}
          className="text-gray-400 hover:text-gray-200 mr-3"
        >
          {isExpanded ? '▼' : '▶'}
        </button>

        {/* Delete Button */}
        <button
          onClick={() => onRemove(node.id)}
          className="text-red-400 hover:text-red-300"
          title="Remove node"
        >
          🗑
        </button>
      </div>

      {/* Expanded Details */}
      {isExpanded && (
        <div className="px-3 pb-3 pt-0 space-y-3 border-t border-gray-600 mt-2">
          {/* Method Notes */}
          <div>
            <label className="block text-xs font-medium text-gray-400 mb-1">
              Exploitation Method
            </label>
            <textarea
              value={node.method_notes || ''}
              onChange={(e) => onUpdate(node.id, { method_notes: e.target.value })}
              rows={2}
              className="w-full px-2 py-1 bg-gray-600 border border-gray-500 rounded text-gray-100 text-sm"
              placeholder="How was this compromised?"
            />
          </div>

          {/* Branch Point */}
          <div>
            <label className="flex items-center text-sm text-gray-300">
              <input
                type="checkbox"
                checked={node.is_branch_point || false}
                onChange={(e) =>
                  onUpdate(node.id, { is_branch_point: e.target.checked })
                }
                className="mr-2"
              />
              Mark as Branch Point
            </label>
          </div>

          {/* Branch Description (conditional) */}
          {node.is_branch_point && (
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1">
                Branch Description
              </label>
              <textarea
                value={node.branch_description || ''}
                onChange={(e) =>
                  onUpdate(node.id, { branch_description: e.target.value })
                }
                rows={1}
                className="w-full px-2 py-1 bg-gray-600 border border-gray-500 rounded text-gray-100 text-sm"
                placeholder="Describe alternative path"
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const AttackChainEditor: React.FC<AttackChainEditorProps> = ({
  chainId,
  projectId,
  isOpen,
  onClose,
  onSave,
  onNodeSelect,
}) => {
  const { data: chain, isLoading, error } = useAttackChain(chainId);
  const updateMutation = useUpdateAttackChain(chainId, projectId);

  // Local editor state
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [color, setColor] = useState('#FF6B35');
  const [nodes, setNodes] = useState<EditableNode[]>([]);
  const [expandedNodeIds, setExpandedNodeIds] = useState<Set<string>>(new Set());
  const [isSelectionMode, setIsSelectionMode] = useState(false);
  const [insertPosition, setInsertPosition] = useState<number | null>(null);
  const [validationErrors, setValidationErrors] = useState<{
    name?: string;
    color?: string;
    nodes?: string;
  }>({});

  // Drag-and-drop sensors
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  // Load chain data into local state when available
  useEffect(() => {
    if (chain && chain.id === chainId) {
      setName(chain.name);
      setDescription(chain.description || '');
      setColor(chain.color);
      // Convert chain nodes to editable nodes
      setNodes(
        chain.nodes.map((node) => ({
          id: node.id,
          entity_type: node.entity_type,
          entity_id: node.entity_id,
          sequence_order: node.sequence_order,
          method_notes: node.method_notes,
          is_branch_point: node.is_branch_point,
          branch_description: node.branch_description,
        }))
      );
    }
  }, [chainId]); // Only re-run when chainId changes

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;

    if (over && active.id !== over.id) {
      setNodes((items) => {
        const oldIndex = items.findIndex((i) => i.id === active.id);
        const newIndex = items.findIndex((i) => i.id === over.id);
        const reordered = arrayMove(items, oldIndex, newIndex);

        // Update sequence_order
        return reordered.map((node, idx) => ({
          ...node,
          sequence_order: idx + 1,
        }));
      });
    }
  };

  const handleRemoveNode = (nodeId: string) => {
    if (nodes.length === 1) {
      alert('Cannot remove the last node. Chain must have at least one node.');
      return;
    }

    if (window.confirm('Remove this node from the chain?')) {
      setNodes((prev) => {
        const filtered = prev.filter((n) => n.id !== nodeId);
        // Resequence
        return filtered.map((node, idx) => ({
          ...node,
          sequence_order: idx + 1,
        }));
      });
    }
  };

  const handleUpdateNode = (nodeId: string, updates: Partial<EditableNode>) => {
    setNodes((prev) =>
      prev.map((node) => (node.id === nodeId ? { ...node, ...updates } : node))
    );
  };

  const handleToggleExpand = (nodeId: string) => {
    setExpandedNodeIds((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(nodeId)) {
        newSet.delete(nodeId);
      } else {
        newSet.add(nodeId);
      }
      return newSet;
    });
  };

  const handleStartAddingNode = (position?: number) => {
    setInsertPosition(position ?? nodes.length);
    setIsSelectionMode(true);

    if (onNodeSelect) {
      onNodeSelect((nodeId: string) => {
        const [entityType, entityId] = nodeId.split('_');
        const newNode: EditableNode = {
          id: `temp-${Date.now()}`, // Temporary ID for frontend
          entity_type: entityType as 'host' | 'service',
          entity_id: entityId,
          sequence_order: insertPosition ?? nodes.length + 1,
          method_notes: '',
          is_branch_point: false,
        };

        setNodes((prev) => {
          const updated = [...prev];
          updated.splice(insertPosition ?? prev.length, 0, newNode);
          // Resequence
          return updated.map((node, idx) => ({
            ...node,
            sequence_order: idx + 1,
          }));
        });

        setIsSelectionMode(false);
        setInsertPosition(null);
      });
    }
  };

  const handleCancelSelection = () => {
    setIsSelectionMode(false);
    setInsertPosition(null);
  };

  const validateForm = (): boolean => {
    const errors: typeof validationErrors = {};

    if (!name || name.trim().length < 3) {
      errors.name = 'Chain name must be at least 3 characters';
    }

    if (!/^#[0-9A-F]{6}$/i.test(color)) {
      errors.color = 'Invalid color format (must be hex: #RRGGBB)';
    }

    if (nodes.length === 0) {
      errors.nodes = 'Chain must have at least one node';
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSave = async () => {
    if (!validateForm()) {
      return;
    }

    try {
      const updateData: {
        name?: string;
        description?: string;
        color?: string;
        nodes?: AttackChainNodeCreate[];
      } = {
        name: name.trim(),
        description: description.trim() || undefined,
        color,
        nodes: nodes.map((node) => ({
          entity_type: node.entity_type,
          entity_id: node.entity_id,
          sequence_order: node.sequence_order,
          method_notes: node.method_notes,
          is_branch_point: node.is_branch_point,
          branch_description: node.branch_description,
        })),
      };

      const updatedChain = await updateMutation.mutateAsync(updateData);

      if (onSave) {
        onSave(updatedChain);
      }

      handleClose();
    } catch (error) {
      console.error('Failed to update attack chain:', error);
      alert('Failed to save changes. Please try again.');
    }
  };

  const handleClose = () => {
    setName('');
    setDescription('');
    setColor('#FF6B35');
    setNodes([]);
    setExpandedNodeIds(new Set());
    setIsSelectionMode(false);
    setInsertPosition(null);
    setValidationErrors({});
    onClose();
  };

  if (!isOpen) return null;

  if (isLoading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
          <div className="text-gray-100">Loading chain data...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-6">
          <div className="text-red-400">Error loading chain: {String(error)}</div>
          <button
            onClick={handleClose}
            className="mt-4 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-100 rounded"
          >
            Close
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-gray-800 border border-gray-700 rounded-lg p-6 max-w-3xl w-full max-h-[85vh] overflow-y-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold text-gray-100">Edit Attack Chain</h2>
          <button
            onClick={handleClose}
            className="text-gray-400 hover:text-gray-200 text-2xl leading-none"
          >
            ✕
          </button>
        </div>

        {/* Basic Info Section */}
        <div className="space-y-4 mb-6">
          <h3 className="text-lg font-semibold text-gray-200 border-b border-gray-600 pb-2">
            Basic Info
          </h3>

          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Chain Name *
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-gray-100"
              placeholder="e.g., Web Server to Domain Controller"
            />
            {validationErrors.name && (
              <p className="text-red-400 text-sm mt-1">{validationErrors.name}</p>
            )}
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-gray-100"
              placeholder="Describe the attack path..."
            />
          </div>

          {/* Color */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Color
            </label>
            <div className="flex items-center space-x-2">
              <input
                type="color"
                value={color}
                onChange={(e) => setColor(e.target.value)}
                className="w-12 h-10 border border-gray-600 rounded cursor-pointer"
              />
              <span className="text-gray-400 text-sm">{color}</span>
            </div>
            {validationErrors.color && (
              <p className="text-red-400 text-sm mt-1">{validationErrors.color}</p>
            )}
          </div>
        </div>

        {/* Node Management Section */}
        <div className="space-y-4 mb-6">
          <div className="flex justify-between items-center border-b border-gray-600 pb-2">
            <h3 className="text-lg font-semibold text-gray-200">Node Management</h3>
            {!isSelectionMode ? (
              <button
                onClick={() => handleStartAddingNode()}
                className="px-3 py-1 bg-green-600 hover:bg-green-700 text-white text-sm rounded"
              >
                + Add Node
              </button>
            ) : (
              <button
                onClick={handleCancelSelection}
                className="px-3 py-1 bg-red-600 hover:bg-red-700 text-white text-sm rounded"
              >
                Cancel Selection
              </button>
            )}
          </div>

          {isSelectionMode && (
            <div className="bg-blue-900 bg-opacity-30 border border-blue-600 rounded p-3 text-sm text-blue-200">
              Click a node on the graph to add it at position {(insertPosition ?? 0) + 1}
            </div>
          )}

          {validationErrors.nodes && (
            <p className="text-red-400 text-sm">{validationErrors.nodes}</p>
          )}

          {/* Draggable Node List */}
          <div className="max-h-96 overflow-y-auto">
            {nodes.length === 0 ? (
              <div className="text-gray-500 text-sm text-center py-8 border border-gray-700 rounded">
                No nodes in chain
              </div>
            ) : (
              <DndContext
                sensors={sensors}
                collisionDetection={closestCenter}
                onDragEnd={handleDragEnd}
              >
                <SortableContext
                  items={nodes.map((n) => n.id)}
                  strategy={verticalListSortingStrategy}
                >
                  {nodes.map((node, index) => (
                    <SortableNodeItem
                      key={node.id}
                      node={node}
                      index={index}
                      onRemove={handleRemoveNode}
                      onUpdate={handleUpdateNode}
                      expandedIds={expandedNodeIds}
                      onToggleExpand={handleToggleExpand}
                    />
                  ))}
                </SortableContext>
              </DndContext>
            )}
          </div>
        </div>

        {/* Footer Buttons */}
        <div className="flex justify-between pt-4 border-t border-gray-600">
          <button
            onClick={handleClose}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-100 rounded"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={updateMutation.isPending}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default AttackChainEditor;
