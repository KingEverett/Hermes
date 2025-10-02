import React from 'react';
import { NetworkNode } from '../../types/network';
import { DetailTabs } from '../details/DetailTabs';

interface NodeDetailsProps {
  node: NetworkNode;
  projectId: string;
  onNodeSelect?: (nodeId: string, nodeType: 'host' | 'service') => void;
}

export const NodeDetails: React.FC<NodeDetailsProps> = ({ node, projectId, onNodeSelect }) => {
  if (!node) {
    return (
      <div className="flex items-center justify-center h-full text-gray-400">
        <div className="text-center">
          <svg
            className="w-16 h-16 mx-auto mb-4 text-gray-600"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <p>Select a node to view details</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col text-gray-100">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-700 flex-shrink-0">
        <div className="flex items-center gap-2 mb-1">
          <span className={`px-2 py-1 rounded text-xs font-semibold ${
            node.type === 'host' ? 'bg-blue-600 text-white' : 'bg-green-600 text-white'
          }`}>
            {node.type.toUpperCase()}
          </span>
        </div>
        <h2 className="text-xl font-semibold">{node.label}</h2>
      </div>

      {/* Detail Tabs Content */}
      <div className="flex-1 overflow-hidden">
        <DetailTabs
          nodeType={node.type}
          nodeId={node.id}
          projectId={projectId}
        />
      </div>
    </div>
  );
};
