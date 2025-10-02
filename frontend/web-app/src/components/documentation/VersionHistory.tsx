import React, { useState } from 'react';
import { useVersionHistory, useRollback } from '../../hooks/useDocumentation';
import MDEditor from '@uiw/react-md-editor';

interface VersionHistoryProps {
  documentationId: string;
}

/**
 * Component displaying version history with rollback functionality
 */
export const VersionHistory: React.FC<VersionHistoryProps> = ({
  documentationId,
}) => {
  const { data: versions, isLoading, error } = useVersionHistory(documentationId);
  const rollbackMutation = useRollback(documentationId);
  const [selectedVersion, setSelectedVersion] = useState<string | null>(null);
  const [showPreview, setShowPreview] = useState(false);

  const handleRollback = (versionId: string) => {
    if (
      window.confirm(
        'Are you sure? This will create a new version with the content from the selected version.'
      )
    ) {
      rollbackMutation.mutate(versionId);
    }
  };

  const handlePreview = (versionId: string) => {
    setSelectedVersion(versionId);
    setShowPreview(true);
  };

  const selectedVersionData = versions?.find((v) => v.id === selectedVersion);

  if (isLoading) {
    return (
      <div className="p-4 bg-gray-50 rounded">
        <div className="text-gray-600 text-sm">Loading version history...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-50 border border-red-200 rounded">
        <div className="text-red-800 text-sm">Error loading version history</div>
      </div>
    );
  }

  if (!versions || versions.length === 0) {
    return (
      <div className="p-4 bg-gray-50 rounded">
        <div className="text-gray-600 text-sm">No version history available</div>
      </div>
    );
  }

  return (
    <div className="version-history bg-gray-50 rounded border border-gray-200">
      <div className="p-3 border-b border-gray-200 bg-gray-100">
        <h4 className="font-semibold text-sm text-gray-800">Version History</h4>
      </div>

      <div className="max-h-64 overflow-y-auto">
        {versions.map((version, index) => (
          <div
            key={version.id}
            className={`p-3 border-b border-gray-200 hover:bg-gray-100 ${
              index === 0 ? 'bg-blue-50' : ''
            }`}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-semibold text-sm text-gray-800">
                    Version {version.version}
                  </span>
                  {index === 0 && (
                    <span className="px-2 py-0.5 text-xs bg-blue-100 text-blue-800 rounded">
                      Current
                    </span>
                  )}
                </div>
                <div className="text-xs text-gray-600">
                  {new Date(version.created_at).toLocaleString()}
                </div>
                {version.author && (
                  <div className="text-xs text-gray-500 mt-1">
                    Author: {version.author}
                  </div>
                )}
              </div>

              <div className="flex gap-2 ml-3">
                <button
                  onClick={() => handlePreview(version.id)}
                  className="px-2 py-1 text-xs text-blue-600 hover:bg-blue-100 rounded border border-blue-300"
                  title="Preview this version"
                >
                  👁️
                </button>
                {index > 0 && (
                  <button
                    onClick={() => handleRollback(version.id)}
                    disabled={rollbackMutation.isPending}
                    className="px-2 py-1 text-xs text-orange-600 hover:bg-orange-100 rounded border border-orange-300 disabled:opacity-50 disabled:cursor-not-allowed"
                    title="Rollback to this version"
                  >
                    ↶ Rollback
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {rollbackMutation.isPending && (
        <div className="p-3 bg-yellow-50 border-t border-yellow-200 text-sm text-yellow-800">
          Rolling back to selected version...
        </div>
      )}

      {rollbackMutation.isError && (
        <div className="p-3 bg-red-50 border-t border-red-200 text-sm text-red-800">
          Error rolling back: {(rollbackMutation.error as Error).message}
        </div>
      )}

      {/* Preview Modal */}
      {showPreview && selectedVersionData && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[80vh] flex flex-col">
            <div className="p-4 border-b border-gray-200 flex items-center justify-between">
              <h3 className="font-semibold text-lg">
                Version {selectedVersionData.version} Preview
              </h3>
              <button
                onClick={() => setShowPreview(false)}
                className="text-gray-500 hover:text-gray-700 text-2xl leading-none"
              >
                ×
              </button>
            </div>

            <div className="p-4 overflow-auto flex-1">
              <div className="prose prose-sm max-w-none" data-color-mode="light">
                <MDEditor.Markdown source={selectedVersionData.content} />
              </div>
            </div>

            <div className="p-4 border-t border-gray-200 flex justify-end gap-2">
              <button
                onClick={() => setShowPreview(false)}
                className="px-4 py-2 text-sm bg-gray-200 text-gray-800 rounded hover:bg-gray-300"
              >
                Close
              </button>
              <button
                onClick={() => {
                  handleRollback(selectedVersionData.id);
                  setShowPreview(false);
                }}
                className="px-4 py-2 text-sm bg-orange-500 text-white rounded hover:bg-orange-600"
              >
                Rollback to This Version
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default VersionHistory;
