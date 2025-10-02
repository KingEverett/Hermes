/**
 * Attack Chain Tree Component
 *
 * Displays attack chains in a tree view in the LeftSidebar.
 * Allows toggling visibility and selecting chains.
 */

import React, { useState } from 'react';
import { useProjectAttackChains, useDeleteAttackChain } from '../../hooks/useAttackChains';
import { useAttackChainVisibilityStore } from '../../stores/attackChainVisibilityStore';
import type { AttackChainListItem } from '../../types/attackChain';

interface AttackChainTreeProps {
  projectId: string;
  onCreateChain: () => void;
  onEditChain: (chainId: string) => void;
  onExportChain?: (chainId: string) => void;
}

const AttackChainTree: React.FC<AttackChainTreeProps> = ({
  projectId,
  onCreateChain,
  onEditChain,
  onExportChain,
}) => {
  const [expandedChains, setExpandedChains] = useState<Set<string>>(new Set());
  const [contextMenu, setContextMenu] = useState<{
    chainId: string;
    x: number;
    y: number;
  } | null>(null);

  const { data: chains, isLoading } = useProjectAttackChains(projectId);
  const deleteMutation = useDeleteAttackChain(projectId);

  const {
    visibleChainIds,
    activeChainId,
    toggleChainVisibility,
    setActiveChain,
  } = useAttackChainVisibilityStore();

  const handleToggleVisibility = (chainId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    toggleChainVisibility(chainId);
  };

  const handleChainClick = (chainId: string) => {
    setActiveChain(chainId === activeChainId ? null : chainId);
  };

  const handleToggleExpand = (chainId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setExpandedChains((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(chainId)) {
        newSet.delete(chainId);
      } else {
        newSet.add(chainId);
      }
      return newSet;
    });
  };

  const handleContextMenu = (chainId: string, e: React.MouseEvent) => {
    e.preventDefault();
    setContextMenu({ chainId, x: e.clientX, y: e.clientY });
  };

  const handleDeleteChain = async (chainId: string) => {
    if (window.confirm('Are you sure you want to delete this attack chain?')) {
      await deleteMutation.mutateAsync(chainId);
    }
    setContextMenu(null);
  };

  const handleEditChain = (chainId: string) => {
    onEditChain(chainId);
    setContextMenu(null);
  };

  const handleExportChain = (chainId: string) => {
    if (onExportChain) {
      onExportChain(chainId);
    }
    setContextMenu(null);
  };

  // Close context menu when clicking outside
  React.useEffect(() => {
    const handleClickOutside = () => setContextMenu(null);
    if (contextMenu) {
      document.addEventListener('click', handleClickOutside);
      return () => document.removeEventListener('click', handleClickOutside);
    }
  }, [contextMenu]);

  if (isLoading) {
    return (
      <div className="p-2 text-gray-400 text-sm">Loading attack chains...</div>
    );
  }

  return (
    <div className="border-t border-gray-700 pt-2">
      <div className="flex items-center justify-between px-2 mb-2">
        <h3 className="text-sm font-semibold text-gray-100">Attack Chains</h3>
        <button
          onClick={onCreateChain}
          className="text-xs px-2 py-1 bg-gray-700 hover:bg-gray-600 text-gray-100 rounded"
          title="Create new attack chain (C)"
        >
          + New
        </button>
      </div>

      {!chains || chains.length === 0 ? (
        <div className="px-2 text-gray-500 text-xs">
          No attack chains yet. Click "+ New" to create one.
        </div>
      ) : (
        <div className="space-y-1">
          {chains.map((chain) => (
            <div key={chain.id} className="text-sm">
              {/* Chain header */}
              <div
                className={`
                  flex items-center px-2 py-1.5 hover:bg-gray-700 cursor-pointer rounded
                  ${activeChainId === chain.id ? 'bg-gray-700' : ''}
                `}
                onClick={() => handleChainClick(chain.id)}
                onContextMenu={(e) => handleContextMenu(chain.id, e)}
              >
                {/* Expand/collapse icon */}
                <button
                  onClick={(e) => handleToggleExpand(chain.id, e)}
                  className="mr-1 text-gray-400 hover:text-gray-200"
                >
                  {expandedChains.has(chain.id) ? '▼' : '▶'}
                </button>

                {/* Visibility toggle icon */}
                <button
                  onClick={(e) => handleToggleVisibility(chain.id, e)}
                  className="mr-2"
                  title={
                    visibleChainIds.has(chain.id)
                      ? 'Hide chain (V)'
                      : 'Show chain (V)'
                  }
                >
                  {visibleChainIds.has(chain.id) ? (
                    <svg className="w-4 h-4 text-gray-300" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M10 12a2 2 0 100-4 2 2 0 000 4z" />
                      <path fillRule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clipRule="evenodd" />
                    </svg>
                  ) : (
                    <svg className="w-4 h-4 text-gray-500" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M3.707 2.293a1 1 0 00-1.414 1.414l14 14a1 1 0 001.414-1.414l-1.473-1.473A10.014 10.014 0 0019.542 10C18.268 5.943 14.478 3 10 3a9.958 9.958 0 00-4.512 1.074l-1.78-1.781zm4.261 4.26l1.514 1.515a2.003 2.003 0 012.45 2.45l1.514 1.514a4 4 0 00-5.478-5.478z" clipRule="evenodd" />
                      <path d="M12.454 16.697L9.75 13.992a4 4 0 01-3.742-3.741L2.335 6.578A9.98 9.98 0 00.458 10c1.274 4.057 5.065 7 9.542 7 .847 0 1.669-.105 2.454-.303z" />
                    </svg>
                  )}
                </button>

                {/* Color dot */}
                <div
                  className="w-3 h-3 rounded-full mr-2"
                  style={{ backgroundColor: chain.color }}
                />

                {/* Chain name */}
                <span className="flex-1 text-gray-100 truncate">{chain.name}</span>

                {/* Node count badge */}
                <span className="text-xs text-gray-400 ml-2">
                  {chain.node_count} {chain.node_count === 1 ? 'node' : 'nodes'}
                </span>
              </div>

              {/* Expanded node list */}
              {expandedChains.has(chain.id) && (
                <div className="ml-8 text-xs text-gray-400 py-1">
                  {chain.description && (
                    <div className="mb-1 italic">{chain.description}</div>
                  )}
                  {chain.node_count > 0 ? (
                    <div>Path with {chain.node_count} hops</div>
                  ) : (
                    <div>No nodes yet</div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Context menu */}
      {contextMenu && (
        <div
          className="fixed bg-gray-800 border border-gray-700 rounded shadow-lg py-1 z-50"
          style={{ left: contextMenu.x, top: contextMenu.y }}
        >
          <button
            onClick={() => handleEditChain(contextMenu.chainId)}
            className="w-full px-4 py-2 text-left text-sm text-gray-100 hover:bg-gray-700"
          >
            Edit
          </button>
          {onExportChain && (
            <button
              onClick={() => handleExportChain(contextMenu.chainId)}
              className="w-full px-4 py-2 text-left text-sm text-gray-100 hover:bg-gray-700"
            >
              Export
            </button>
          )}
          <button
            onClick={() => handleDeleteChain(contextMenu.chainId)}
            className="w-full px-4 py-2 text-left text-sm text-red-400 hover:bg-gray-700"
          >
            Delete
          </button>
        </div>
      )}
    </div>
  );
};

export default AttackChainTree;
