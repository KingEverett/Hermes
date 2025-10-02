import React from 'react';
import { NodeDetails } from './NodeDetails';
import { ProjectSummary } from './ProjectSummary';
import { NetworkNode } from '../../types/network';

interface RightPanelProps {
  selectedNode: NetworkNode | null;
  projectId: string;
  onNodeSelect?: (nodeId: string, nodeType: 'host' | 'service') => void;
}

export const RightPanel: React.FC<RightPanelProps> = ({ selectedNode, projectId, onNodeSelect }) => {
  return (
    <div className="h-full bg-gray-800 border-l border-gray-700 overflow-hidden">
      {selectedNode ? (
        <NodeDetails
          node={selectedNode}
          projectId={projectId}
          onNodeSelect={onNodeSelect}
        />
      ) : (
        <div className="p-4 overflow-y-auto h-full">
          <ProjectSummary />
        </div>
      )}
    </div>
  );
};
