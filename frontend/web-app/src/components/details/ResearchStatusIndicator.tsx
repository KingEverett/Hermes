import React from 'react';
import { useResearchTasks } from '../../hooks/useResearchTasks';

interface ResearchStatusIndicatorProps {
  targetId: string;
  targetType: 'host' | 'service' | 'vulnerability';
}

interface ResearchTask {
  id: string;
  project_id: string;
  target_type: 'service' | 'vulnerability' | 'host';
  target_id: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  source: 'nvd' | 'exploitdb' | 'cisa' | 'manual';
  results?: any;
  error_message?: string;
  retry_count: number;
  created_at: Date | string;
  completed_at?: Date | string;
}

export const ResearchStatusIndicator: React.FC<ResearchStatusIndicatorProps> = ({ targetId, targetType }) => {
  const { data: tasks, isLoading } = useResearchTasks(targetId, targetType);

  const getStatusBadge = (status: string) => {
    const statusStyles = {
      queued: 'bg-gray-600 text-white',
      processing: 'bg-blue-600 text-white',
      completed: 'bg-green-600 text-white',
      failed: 'bg-red-600 text-white',
    };
    return statusStyles[status as keyof typeof statusStyles] || 'bg-gray-600 text-white';
  };

  const getSourceLabel = (source: string) => {
    const sourceLabels = {
      nvd: 'NVD',
      exploitdb: 'ExploitDB',
      cisa: 'CISA KEV',
      manual: 'Manual',
    };
    return sourceLabels[source as keyof typeof sourceLabels] || source;
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'queued':
        return (
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
          </svg>
        );
      case 'processing':
        return (
          <svg className="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        );
      case 'completed':
        return (
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
          </svg>
        );
      case 'failed':
        return (
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
          </svg>
        );
      default:
        return null;
    }
  };

  if (isLoading) {
    return (
      <div className="animate-pulse">
        <div className="h-4 bg-gray-700 rounded w-3/4 mb-3"></div>
        <div className="h-20 bg-gray-700 rounded"></div>
      </div>
    );
  }

  if (!tasks || tasks.length === 0) {
    return (
      <div className="text-gray-400 text-sm bg-gray-800 rounded border border-gray-700 p-4 text-center">
        <svg
          className="w-10 h-10 mx-auto mb-2 text-gray-600"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
          />
        </svg>
        <p>No research tasks initiated</p>
      </div>
    );
  }

  // Calculate progress statistics
  const statusCounts = {
    queued: tasks.filter(t => t.status === 'queued').length,
    processing: tasks.filter(t => t.status === 'processing').length,
    completed: tasks.filter(t => t.status === 'completed').length,
    failed: tasks.filter(t => t.status === 'failed').length,
  };

  const totalTasks = tasks.length;
  const progressPercentage = Math.round((statusCounts.completed / totalTasks) * 100);

  return (
    <div className="space-y-4">
      {/* Progress Bar */}
      <div>
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm text-gray-300">Research Progress</span>
          <span className="text-sm font-semibold text-gray-100">{progressPercentage}%</span>
        </div>
        <div className="w-full bg-gray-700 rounded-full h-2 overflow-hidden">
          <div className="flex h-full">
            {statusCounts.completed > 0 && (
              <div
                className="bg-green-600"
                style={{ width: `${(statusCounts.completed / totalTasks) * 100}%` }}
                title={`${statusCounts.completed} completed`}
              ></div>
            )}
            {statusCounts.processing > 0 && (
              <div
                className="bg-blue-600"
                style={{ width: `${(statusCounts.processing / totalTasks) * 100}%` }}
                title={`${statusCounts.processing} processing`}
              ></div>
            )}
            {statusCounts.failed > 0 && (
              <div
                className="bg-red-600"
                style={{ width: `${(statusCounts.failed / totalTasks) * 100}%` }}
                title={`${statusCounts.failed} failed`}
              ></div>
            )}
            {statusCounts.queued > 0 && (
              <div
                className="bg-gray-600"
                style={{ width: `${(statusCounts.queued / totalTasks) * 100}%` }}
                title={`${statusCounts.queued} queued`}
              ></div>
            )}
          </div>
        </div>
      </div>

      {/* Status Summary */}
      <div className="grid grid-cols-2 gap-2 text-sm">
        {statusCounts.completed > 0 && (
          <div className="bg-green-900/30 border border-green-800 rounded px-3 py-2">
            <div className="text-green-400 text-xs">Completed</div>
            <div className="text-green-300 text-lg font-bold">{statusCounts.completed}</div>
          </div>
        )}
        {statusCounts.processing > 0 && (
          <div className="bg-blue-900/30 border border-blue-800 rounded px-3 py-2">
            <div className="text-blue-400 text-xs">Processing</div>
            <div className="text-blue-300 text-lg font-bold">{statusCounts.processing}</div>
          </div>
        )}
        {statusCounts.queued > 0 && (
          <div className="bg-gray-700 border border-gray-600 rounded px-3 py-2">
            <div className="text-gray-400 text-xs">Queued</div>
            <div className="text-gray-300 text-lg font-bold">{statusCounts.queued}</div>
          </div>
        )}
        {statusCounts.failed > 0 && (
          <div className="bg-red-900/30 border border-red-800 rounded px-3 py-2">
            <div className="text-red-400 text-xs">Failed</div>
            <div className="text-red-300 text-lg font-bold">{statusCounts.failed}</div>
          </div>
        )}
      </div>

      {/* Task List */}
      <div className="space-y-2">
        <h4 className="text-sm font-semibold text-gray-300">Research Tasks</h4>
        {tasks.map((task) => (
          <div
            key={task.id}
            className="bg-gray-800 border border-gray-700 rounded p-3 text-sm"
          >
            <div className="flex items-center justify-between gap-2 mb-1">
              <div className="flex items-center gap-2">
                <span className={`px-2 py-0.5 rounded text-xs font-semibold ${getStatusBadge(task.status)}`}>
                  {getStatusIcon(task.status)}
                </span>
                <span className="text-gray-100 font-medium">{getSourceLabel(task.source)}</span>
              </div>
              <span className={`px-2 py-0.5 rounded text-xs ${getStatusBadge(task.status)}`}>
                {task.status.toUpperCase()}
              </span>
            </div>

            {/* Error Message for Failed Tasks */}
            {task.status === 'failed' && task.error_message && (
              <div className="mt-2 text-xs text-red-400 bg-red-900/20 rounded p-2">
                <div className="font-semibold mb-1">Error:</div>
                <div>{task.error_message}</div>
                {task.retry_count > 0 && (
                  <div className="mt-1 text-red-300">Retry count: {task.retry_count}</div>
                )}
              </div>
            )}

            {/* Completion Time */}
            {task.status === 'completed' && task.completed_at && (
              <div className="mt-1 text-xs text-gray-500">
                Completed: {new Date(task.completed_at).toLocaleString('en-US', {
                  month: 'short',
                  day: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
