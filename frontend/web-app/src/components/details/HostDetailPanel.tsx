import React from 'react';
import { useHostDetails } from '../../hooks/useHostDetails';
import { copyToClipboard } from '../../utils/clipboard';

interface HostDetailPanelProps {
  hostId: string;
}

export const HostDetailPanel: React.FC<HostDetailPanelProps> = ({ hostId }) => {
  const { data: host, isLoading, error } = useHostDetails(hostId);

  const handleCopy = async (text: string) => {
    const success = await copyToClipboard(text);
    if (success) {
      // TODO: Add toast notification in future story
      console.log('Copied to clipboard');
    }
  };

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-6 bg-gray-700 rounded w-3/4"></div>
        <div className="h-4 bg-gray-700 rounded w-1/2"></div>
        <div className="h-4 bg-gray-700 rounded w-2/3"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-red-400 p-4 bg-red-900/20 rounded border border-red-800">
        <p className="font-semibold mb-2">Unable to load host details</p>
        <p className="text-sm">{error instanceof Error ? error.message : 'An error occurred'}</p>
      </div>
    );
  }

  if (!host) {
    return (
      <div className="text-gray-400 p-4">
        <p>Host not found</p>
      </div>
    );
  }

  const getStatusBadge = (status: string) => {
    const statusColors = {
      up: 'bg-green-600 text-white',
      down: 'bg-red-600 text-white',
      filtered: 'bg-yellow-600 text-white',
    };
    return statusColors[status as keyof typeof statusColors] || 'bg-gray-600 text-white';
  };

  const formatDate = (date: Date | string) => {
    return new Date(date).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="space-y-6">
      {/* IP Address Section */}
      <div>
        <label className="text-sm text-gray-400 block mb-1">IP Address</label>
        <div className="flex items-center gap-2">
          <span className="font-mono text-lg text-gray-100">{host.ip_address}</span>
          <button
            onClick={() => handleCopy(host.ip_address)}
            className="text-blue-400 hover:text-blue-300 text-xs px-2 py-1 rounded border border-blue-600 hover:border-blue-500"
            title="Copy to clipboard"
          >
            Copy
          </button>
        </div>
      </div>

      {/* Hostname Section */}
      <div>
        <label className="text-sm text-gray-400 block mb-1">Hostname</label>
        <span className="text-gray-100">
          {host.hostname || <span className="text-gray-500">N/A</span>}
        </span>
      </div>

      {/* Status Section */}
      <div>
        <label className="text-sm text-gray-400 block mb-1">Status</label>
        <span className={`inline-block px-3 py-1 rounded text-sm font-semibold ${getStatusBadge(host.status)}`}>
          {host.status.toUpperCase()}
        </span>
      </div>

      {/* Operating System Section */}
      <div>
        <label className="text-sm text-gray-400 block mb-1">Operating System</label>
        {host.os_family || host.os_details ? (
          <div className="text-gray-100">
            {host.os_family && <div className="font-semibold">{host.os_family}</div>}
            {host.os_details && <div className="text-sm text-gray-300">{host.os_details}</div>}
          </div>
        ) : (
          <span className="text-gray-500">OS not detected</span>
        )}
      </div>

      {/* MAC Address Section */}
      {host.mac_address && (
        <div>
          <label className="text-sm text-gray-400 block mb-1">MAC Address</label>
          <span className="font-mono text-gray-100">{host.mac_address}</span>
        </div>
      )}

      {/* Confidence Score Section */}
      {host.confidence_score !== undefined && (
        <div>
          <label className="text-sm text-gray-400 block mb-1">Confidence Score</label>
          <div className="flex items-center gap-2">
            <div className="flex-1 bg-gray-700 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full"
                style={{ width: `${host.confidence_score * 100}%` }}
              ></div>
            </div>
            <span className="text-sm text-gray-300">{Math.round(host.confidence_score * 100)}%</span>
          </div>
        </div>
      )}

      {/* Open Ports Section */}
      <div>
        <label className="text-sm text-gray-400 block mb-1">Open Ports</label>
        <div className="text-gray-100">
          {host.metadata?.open_ports_count ? (
            <span className="font-semibold text-lg">{host.metadata.open_ports_count}</span>
          ) : (
            <span className="text-gray-500">No ports detected</span>
          )}
        </div>
      </div>

      {/* Vulnerability Summary Section */}
      <div>
        <label className="text-sm text-gray-400 block mb-1">Vulnerability Summary</label>
        {host.metadata?.vulnerability_summary ? (
          <div className="grid grid-cols-2 gap-2">
            {host.metadata.vulnerability_summary.critical > 0 && (
              <div className="bg-red-900/30 border border-red-800 rounded px-3 py-2">
                <div className="text-red-400 text-xs font-semibold">Critical</div>
                <div className="text-red-300 text-lg font-bold">{host.metadata.vulnerability_summary.critical}</div>
              </div>
            )}
            {host.metadata.vulnerability_summary.high > 0 && (
              <div className="bg-orange-900/30 border border-orange-800 rounded px-3 py-2">
                <div className="text-orange-400 text-xs font-semibold">High</div>
                <div className="text-orange-300 text-lg font-bold">{host.metadata.vulnerability_summary.high}</div>
              </div>
            )}
            {host.metadata.vulnerability_summary.medium > 0 && (
              <div className="bg-yellow-900/30 border border-yellow-800 rounded px-3 py-2">
                <div className="text-yellow-400 text-xs font-semibold">Medium</div>
                <div className="text-yellow-300 text-lg font-bold">{host.metadata.vulnerability_summary.medium}</div>
              </div>
            )}
            {host.metadata.vulnerability_summary.low > 0 && (
              <div className="bg-blue-900/30 border border-blue-800 rounded px-3 py-2">
                <div className="text-blue-400 text-xs font-semibold">Low</div>
                <div className="text-blue-300 text-lg font-bold">{host.metadata.vulnerability_summary.low}</div>
              </div>
            )}
          </div>
        ) : (
          <span className="text-gray-500">No vulnerabilities identified</span>
        )}
      </div>

      {/* Timestamps Section */}
      <div className="border-t border-gray-700 pt-4 space-y-2">
        <div>
          <label className="text-xs text-gray-500 block">First Seen</label>
          <span className="text-sm text-gray-300">{formatDate(host.first_seen)}</span>
        </div>
        <div>
          <label className="text-xs text-gray-500 block">Last Seen</label>
          <span className="text-sm text-gray-300">{formatDate(host.last_seen)}</span>
        </div>
      </div>
    </div>
  );
};
