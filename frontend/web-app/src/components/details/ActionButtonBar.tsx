import React, { useState } from 'react';
import { copyToClipboard } from '../../utils/clipboard';

interface ActionButtonBarProps {
  nodeType: 'host' | 'service';
  nodeId: string;
  nodeData?: any;
  onAddNote: () => void;
  onMarkReviewed: () => void;
  onExport: () => void;
}

export const ActionButtonBar: React.FC<ActionButtonBarProps> = ({
  nodeType,
  nodeId,
  nodeData,
  onAddNote,
  onMarkReviewed,
  onExport,
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopyInfo = async () => {
    let textToCopy = '';

    if (nodeType === 'host' && nodeData) {
      textToCopy = `Host Information:
IP Address: ${nodeData.ip_address || 'N/A'}
Hostname: ${nodeData.hostname || 'N/A'}
Status: ${nodeData.status || 'N/A'}
OS: ${nodeData.os_family || 'N/A'} ${nodeData.os_details || ''}
MAC Address: ${nodeData.mac_address || 'N/A'}
Open Ports: ${nodeData.metadata?.open_ports_count || 0}`;
    } else if (nodeType === 'service' && nodeData) {
      textToCopy = `Service Information:
Port: ${nodeData.port || 'N/A'}
Protocol: ${nodeData.protocol || 'N/A'}
Service: ${nodeData.service_name || 'Unknown'}
Product: ${nodeData.product || 'N/A'}
Version: ${nodeData.version || 'N/A'}
CPE: ${nodeData.cpe || 'N/A'}`;
    } else {
      textToCopy = `${nodeType.toUpperCase()} ID: ${nodeId}`;
    }

    const success = await copyToClipboard(textToCopy);
    if (success) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const buttonClasses = "bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded text-sm font-semibold transition-colors flex items-center gap-1.5";
  const secondaryButtonClasses = "bg-gray-700 hover:bg-gray-600 text-gray-100 px-3 py-1.5 rounded text-sm font-semibold transition-colors flex items-center gap-1.5";

  return (
    <div className="flex flex-wrap gap-2 p-4 border-t border-gray-700 bg-gray-800/50">
      {/* Add Note Button */}
      <button
        onClick={onAddNote}
        className={buttonClasses}
        title="Add a note to this entity"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
        </svg>
        Add Note
      </button>

      {/* Mark Reviewed Button */}
      <button
        onClick={onMarkReviewed}
        className={secondaryButtonClasses}
        title="Mark this entity as reviewed"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        </svg>
        Mark Reviewed
      </button>

      {/* Export Details Button */}
      <button
        onClick={onExport}
        className={secondaryButtonClasses}
        title="Export entity details"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
        Export
      </button>

      {/* Copy Info Button */}
      <button
        onClick={handleCopyInfo}
        className={copied ? "bg-green-600 text-white px-3 py-1.5 rounded text-sm font-semibold flex items-center gap-1.5" : secondaryButtonClasses}
        title="Copy key details to clipboard"
      >
        {copied ? (
          <>
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            Copied!
          </>
        ) : (
          <>
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
            Copy Info
          </>
        )}
      </button>
    </div>
  );
};
