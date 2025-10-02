/**
 * ProjectView page
 *
 * Main project visualization page displaying network topology graph.
 */

import React, { useState } from 'react';
import { NetworkGraph } from '../components/visualization/NetworkGraph';
import { useNetworkData } from '../hooks/useNetworkData';
import { ThreePanelLayout } from '../components/layout/ThreePanelLayout';
import { LeftSidebar } from '../components/layout/LeftSidebar';
import { RightPanel } from '../components/layout/RightPanel';
import { NetworkNode } from '../types/network';

interface ProjectViewProps {
  projectId: string;
}

export const ProjectView: React.FC<ProjectViewProps> = ({ projectId }) => {
  const { data, isLoading, error } = useNetworkData(projectId);
  const [selectedNode, setSelectedNode] = useState<NetworkNode | null>(null);

  // Adapter to convert NetworkGraph's nodeIds array to NetworkNode for RightPanel
  const handleNodeSelect = (nodeIds: string[]) => {
    if (nodeIds.length === 0) {
      setSelectedNode(null);
      return;
    }

    // Find the selected node in the topology data
    const nodeId = nodeIds[0]; // Take first selected node
    const graphNode = data?.nodes.find(n => n.id === nodeId);

    if (graphNode) {
      const networkNode: NetworkNode = {
        id: graphNode.id,
        type: graphNode.type,
        label: graphNode.label,
        data: graphNode,
      };
      setSelectedNode(networkNode);
    }
  };

  if (isLoading) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-gray-900">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
          <p className="text-gray-100">Loading network topology...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-gray-900">
        <div className="text-center max-w-md">
          <div className="text-red-500 text-5xl mb-4">⚠️</div>
          <h2 className="text-xl font-semibold text-gray-100 mb-2">Failed to load topology</h2>
          <p className="text-gray-400">{error.message}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-gray-900">
        <p className="text-gray-100">No topology data available</p>
      </div>
    );
  }

  return (
    <ThreePanelLayout
      left={<LeftSidebar />}
      center={
        <div className="h-full relative">
          <NetworkGraph
            topology={data}
            onNodeSelect={handleNodeSelect}
            selectedNodeIds={selectedNode ? [selectedNode.id] : []}
          />
        </div>
      }
      right={<RightPanel selectedNode={selectedNode} projectId={projectId} />}
    />
  );
};

export default ProjectView;
