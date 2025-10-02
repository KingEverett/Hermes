/**
 * Attack Chain Creator Modal
 *
 * Multi-step modal for creating new attack chains with node selection
 */

import React, { useState } from 'react';
import { useCreateAttackChain } from '../../hooks/useAttackChains';
import type { AttackChainNodeCreate } from '../../types/attackChain';

interface AttackChainCreatorProps {
  projectId: string;
  isOpen: boolean;
  onClose: () => void;
  onNodeSelect?: (callback: (nodeId: string) => void) => void;
}

const AttackChainCreator: React.FC<AttackChainCreatorProps> = ({
  projectId,
  isOpen,
  onClose,
  onNodeSelect,
}) => {
  const [step, setStep] = useState(1);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [color, setColor] = useState('#FF6B35');
  const [nodes, setNodes] = useState<AttackChainNodeCreate[]>([]);
  const [isSelecting, setIsSelecting] = useState(false);

  const createMutation = useCreateAttackChain(projectId);

  const handleStartSelection = () => {
    setIsSelecting(true);
    if (onNodeSelect) {
      onNodeSelect((nodeId: string) => {
        const [entityType, entityId] = nodeId.split('_');
        const newNode: AttackChainNodeCreate = {
          entity_type: entityType as 'host' | 'service',
          entity_id: entityId,
          sequence_order: nodes.length + 1,
          method_notes: '',
          is_branch_point: false,
        };
        setNodes((prev) => [...prev, newNode]);
      });
    }
  };

  const handleStopSelection = () => {
    setIsSelecting(false);
  };

  const handleRemoveNode = (index: number) => {
    setNodes((prev) => {
      const newNodes = prev.filter((_, i) => i !== index);
      // Reorder sequence
      return newNodes.map((node, i) => ({
        ...node,
        sequence_order: i + 1,
      }));
    });
  };

  const handleUpdateNodeNotes = (index: number, notes: string) => {
    setNodes((prev) =>
      prev.map((node, i) => (i === index ? { ...node, method_notes: notes } : node))
    );
  };

  const handleToggleBranchPoint = (index: number) => {
    setNodes((prev) =>
      prev.map((node, i) =>
        i === index ? { ...node, is_branch_point: !node.is_branch_point } : node
      )
    );
  };

  const handleUpdateBranchDescription = (index: number, desc: string) => {
    setNodes((prev) =>
      prev.map((node, i) =>
        i === index ? { ...node, branch_description: desc } : node
      )
    );
  };

  const handleCreate = async () => {
    if (!name.trim()) {
      alert('Please enter a chain name');
      return;
    }

    try {
      await createMutation.mutateAsync({
        name: name.trim(),
        description: description.trim() || undefined,
        color,
        nodes,
      });
      handleClose();
    } catch (error) {
      console.error('Failed to create attack chain:', error);
      alert('Failed to create attack chain. Please try again.');
    }
  };

  const handleClose = () => {
    setStep(1);
    setName('');
    setDescription('');
    setColor('#FF6B35');
    setNodes([]);
    setIsSelecting(false);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-gray-800 border border-gray-700 rounded-lg p-6 max-w-2xl w-full max-h-[80vh] overflow-y-auto">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold text-gray-100">
            Create Attack Chain {step > 1 && `- Step ${step}/3`}
          </h2>
          <button
            onClick={handleClose}
            className="text-gray-400 hover:text-gray-200"
          >
            ✕
          </button>
        </div>

        {/* Step 1: Basic Info */}
        {step === 1 && (
          <div className="space-y-4">
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
            </div>

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
            </div>

            <div className="flex justify-end space-x-2 pt-4">
              <button
                onClick={handleClose}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-100 rounded"
              >
                Cancel
              </button>
              <button
                onClick={() => setStep(2)}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded"
              >
                Next: Select Nodes
              </button>
            </div>
          </div>
        )}

        {/* Step 2: Node Selection */}
        {step === 2 && (
          <div className="space-y-4">
            <div className="text-sm text-gray-300 mb-2">
              Click nodes on the graph to add them to the chain in sequence.
            </div>

            <div className="flex space-x-2">
              {!isSelecting ? (
                <button
                  onClick={handleStartSelection}
                  className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded"
                >
                  Start Selecting Nodes
                </button>
              ) : (
                <button
                  onClick={handleStopSelection}
                  className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded"
                >
                  Stop Selecting
                </button>
              )}
            </div>

            <div className="border border-gray-700 rounded p-3 max-h-60 overflow-y-auto">
              {nodes.length === 0 ? (
                <div className="text-gray-500 text-sm text-center py-4">
                  No nodes selected yet
                </div>
              ) : (
                <div className="space-y-2">
                  {nodes.map((node, index) => (
                    <div
                      key={index}
                      className="flex items-center space-x-2 bg-gray-700 p-2 rounded"
                    >
                      <span className="text-gray-300 font-mono text-sm">
                        {index + 1}.
                      </span>
                      <span className="text-gray-100 text-sm flex-1">
                        {node.entity_type}: {node.entity_id.substring(0, 8)}...
                      </span>
                      <button
                        onClick={() => handleRemoveNode(index)}
                        className="text-red-400 hover:text-red-300 text-sm"
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="flex justify-between pt-4">
              <button
                onClick={() => setStep(1)}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-100 rounded"
              >
                Back
              </button>
              <div className="space-x-2">
                <button
                  onClick={handleClose}
                  className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-100 rounded"
                >
                  Cancel
                </button>
                <button
                  onClick={() => setStep(3)}
                  disabled={nodes.length === 0}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next: Annotate
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Step 3: Annotations */}
        {step === 3 && (
          <div className="space-y-4">
            <div className="text-sm text-gray-300 mb-2">
              Add method notes for each hop in the attack chain.
            </div>

            <div className="space-y-3 max-h-96 overflow-y-auto">
              {nodes.map((node, index) => (
                <div key={index} className="bg-gray-700 p-3 rounded">
                  <div className="font-medium text-gray-100 mb-2">
                    Hop {index + 1}: {node.entity_type} (
                    {node.entity_id.substring(0, 8)}...)
                  </div>

                  <textarea
                    value={node.method_notes || ''}
                    onChange={(e) => handleUpdateNodeNotes(index, e.target.value)}
                    rows={2}
                    className="w-full px-3 py-2 bg-gray-600 border border-gray-500 rounded text-gray-100 text-sm"
                    placeholder="How did you compromise this? (e.g., SQL injection, credential reuse)"
                  />

                  <div className="mt-2">
                    <label className="flex items-center text-sm text-gray-300">
                      <input
                        type="checkbox"
                        checked={node.is_branch_point || false}
                        onChange={() => handleToggleBranchPoint(index)}
                        className="mr-2"
                      />
                      Branch point (alternative path available)
                    </label>
                  </div>

                  {node.is_branch_point && (
                    <textarea
                      value={node.branch_description || ''}
                      onChange={(e) =>
                        handleUpdateBranchDescription(index, e.target.value)
                      }
                      rows={1}
                      className="w-full mt-2 px-3 py-2 bg-gray-600 border border-gray-500 rounded text-gray-100 text-sm"
                      placeholder="Describe alternative path (e.g., Could pivot to mail server)"
                    />
                  )}
                </div>
              ))}
            </div>

            <div className="flex justify-between pt-4">
              <button
                onClick={() => setStep(2)}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-100 rounded"
              >
                Back
              </button>
              <div className="space-x-2">
                <button
                  onClick={handleClose}
                  className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-100 rounded"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCreate}
                  disabled={createMutation.isPending}
                  className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded disabled:opacity-50"
                >
                  {createMutation.isPending ? 'Creating...' : 'Create Attack Chain'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AttackChainCreator;
