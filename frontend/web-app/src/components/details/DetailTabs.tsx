import React, { useState } from 'react';
import { HostDetailPanel } from './HostDetailPanel';
import { ServiceDetailPanel } from './ServiceDetailPanel';
import { VulnerabilityList } from './VulnerabilityList';
import { ResearchStatusIndicator } from './ResearchStatusIndicator';
import { NotesEditor } from './NotesEditor';
import { useServiceVulnerabilities } from '../../hooks/useServiceVulnerabilities';

interface DetailTabsProps {
  nodeType: 'host' | 'service';
  nodeId: string;
  projectId: string;
}

type TabType = 'details' | 'vulnerabilities' | 'notes';

export const DetailTabs: React.FC<DetailTabsProps> = ({ nodeType, nodeId, projectId }) => {
  const [activeTab, setActiveTab] = useState<TabType>('details');
  const { data: vulnerabilities, isLoading: vulnLoading } = useServiceVulnerabilities(
    nodeType === 'service' ? nodeId : undefined
  );

  const tabClasses = (tab: TabType) => {
    const isActive = activeTab === tab;
    return `px-4 py-2 transition-colors ${
      isActive
        ? 'text-gray-100 border-b-2 border-blue-600'
        : 'text-gray-400 hover:text-gray-100'
    }`;
  };

  return (
    <div className="h-full flex flex-col">
      {/* Tab Headers */}
      <div className="flex border-b border-gray-700 flex-shrink-0">
        <button
          onClick={() => setActiveTab('details')}
          className={tabClasses('details')}
        >
          Technical Details
        </button>
        <button
          onClick={() => setActiveTab('vulnerabilities')}
          className={tabClasses('vulnerabilities')}
        >
          Vulnerabilities & Research
        </button>
        <button
          onClick={() => setActiveTab('notes')}
          className={tabClasses('notes')}
        >
          Notes
        </button>
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === 'details' && (
          nodeType === 'host'
            ? <HostDetailPanel hostId={nodeId} />
            : <ServiceDetailPanel serviceId={nodeId} />
        )}

        {activeTab === 'vulnerabilities' && (
          <div className="space-y-6">
            {/* Research Status */}
            <div>
              <h3 className="text-lg font-semibold text-gray-100 mb-3">Research Status</h3>
              <ResearchStatusIndicator targetId={nodeId} targetType={nodeType} />
            </div>

            {/* Vulnerability List */}
            <div>
              <h3 className="text-lg font-semibold text-gray-100 mb-3">Identified Vulnerabilities</h3>
              {nodeType === 'service' ? (
                <VulnerabilityList vulnerabilities={vulnerabilities || []} loading={vulnLoading} />
              ) : (
                <div className="text-gray-400 text-sm">
                  Vulnerability details for hosts will be aggregated from all services in a future update.
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'notes' && (
          <NotesEditor
            entityType={nodeType}
            entityId={nodeId}
            projectId={projectId}
          />
        )}
      </div>
    </div>
  );
};
