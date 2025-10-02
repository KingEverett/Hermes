/**
 * ExportHistory Component
 * Displays history of export jobs with download and retry capabilities
 */

import React, { useEffect, useState } from 'react';
import { ExportJob } from '../../hooks/useExportProgress';

export interface ExportHistoryProps {
  projectId: string;
  maxItems?: number;
  onRetry?: (jobId: string) => void;
}

const ExportHistory: React.FC<ExportHistoryProps> = ({
  projectId,
  maxItems = 10,
  onRetry
}) => {
  const [exports, setExports] = useState<ExportJob[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchExports = async () => {
      try {
        const response = await fetch(
          `/api/v1/projects/${projectId}/exports?limit=${maxItems}`
        );

        if (!response.ok) {
          throw new Error('Failed to fetch export history');
        }

        const data: ExportJob[] = await response.json();
        setExports(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setIsLoading(false);
      }
    };

    fetchExports();

    // Refresh every 10 seconds
    const intervalId = setInterval(fetchExports, 10000);
    return () => clearInterval(intervalId);
  }, [projectId, maxItems]);

  const handleDownload = (exportJob: ExportJob) => {
    if (exportJob.download_url) {
      window.location.href = exportJob.download_url;
    }
  };

  const getStatusBadge = (status: string) => {
    const badges = {
      pending: 'bg-yellow-900 text-yellow-200 border-yellow-700',
      processing: 'bg-blue-900 text-blue-200 border-blue-700',
      completed: 'bg-green-900 text-green-200 border-green-700',
      failed: 'bg-red-900 text-red-200 border-red-700'
    };

    const label = status.charAt(0).toUpperCase() + status.slice(1);

    return (
      <span className={`px-2 py-1 text-xs font-medium rounded border ${badges[status as keyof typeof badges] || badges.pending}`}>
        {label}
      </span>
    );
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  const getFileSize = (filePath?: string) => {
    // Placeholder - would be provided by API
    return 'N/A';
  };

  if (isLoading) {
    return (
      <div className="p-4 text-center text-gray-400">
        <svg className="animate-spin h-6 w-6 mx-auto mb-2" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
        </svg>
        Loading export history...
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 text-center text-red-400">
        <p>Error loading exports: {error}</p>
      </div>
    );
  }

  if (exports.length === 0) {
    return (
      <div className="p-4 text-center text-gray-400">
        <svg className="h-12 w-12 mx-auto mb-2 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M9 19l3 3m0 0l3-3m-3 3V10" />
        </svg>
        <p>No exports yet</p>
        <p className="text-sm text-gray-500 mt-1">
          Export a graph to see history here
        </p>
      </div>
    );
  }

  return (
    <div className="bg-gray-900 text-gray-100">
      <div className="border-b border-gray-700 px-4 py-3">
        <h3 className="font-semibold text-gray-100">Export History</h3>
        <p className="text-xs text-gray-400 mt-1">
          Recent exports and downloads
        </p>
      </div>

      <div className="overflow-y-auto max-h-96">
        <table className="w-full text-sm">
          <thead className="bg-gray-800 sticky top-0">
            <tr className="border-b border-gray-700">
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-400 uppercase">
                Timestamp
              </th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-400 uppercase">
                Format
              </th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-400 uppercase">
                Status
              </th>
              <th className="px-4 py-2 text-left text-xs font-medium text-gray-400 uppercase">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800">
            {exports.map((exportJob) => (
              <tr key={exportJob.id} className="hover:bg-gray-800 transition-colors">
                <td className="px-4 py-3 text-gray-300">
                  <div className="text-sm">{formatDate(exportJob.created_at)}</div>
                  {exportJob.completed_at && (
                    <div className="text-xs text-gray-500">
                      Completed: {formatDate(exportJob.completed_at)}
                    </div>
                  )}
                </td>
                <td className="px-4 py-3">
                  <span className="uppercase text-xs font-mono bg-gray-700 px-2 py-1 rounded">
                    {exportJob.format}
                  </span>
                </td>
                <td className="px-4 py-3">
                  {getStatusBadge(exportJob.status)}
                  {exportJob.status === 'processing' && exportJob.progress !== undefined && (
                    <div className="mt-1">
                      <div className="w-full bg-gray-700 rounded-full h-1.5">
                        <div
                          className="bg-blue-500 h-1.5 rounded-full transition-all duration-300"
                          style={{ width: `${exportJob.progress}%` }}
                        />
                      </div>
                      <div className="text-xs text-gray-500 mt-0.5">
                        {exportJob.current_item && exportJob.total_items
                          ? `${exportJob.current_item} of ${exportJob.total_items}`
                          : `${exportJob.progress}%`}
                      </div>
                    </div>
                  )}
                  {exportJob.status === 'failed' && exportJob.error_message && (
                    <div className="text-xs text-red-400 mt-1">
                      {exportJob.error_message}
                    </div>
                  )}
                </td>
                <td className="px-4 py-3">
                  <div className="flex gap-2">
                    {exportJob.status === 'completed' && exportJob.download_url && (
                      <button
                        onClick={() => handleDownload(exportJob)}
                        className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white text-xs rounded transition-colors flex items-center gap-1"
                        title="Download"
                      >
                        <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                        </svg>
                        Download
                      </button>
                    )}
                    {exportJob.status === 'failed' && onRetry && (
                      <button
                        onClick={() => onRetry(exportJob.id)}
                        className="px-3 py-1 bg-gray-700 hover:bg-gray-600 text-white text-xs rounded transition-colors flex items-center gap-1"
                        title="Retry"
                      >
                        <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                        Retry
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default ExportHistory;
