/**
 * ExportOptionsModal Component
 * Modal dialog for configuring graph export options
 */

import React, { useState } from 'react';
import { Severity } from '../../services/graphExport';

export interface ExportOptions {
  format: 'svg' | 'png';
  resolution: number; // 1x, 2x, or 4x
  includeLegend: boolean;
  includeMetadata: boolean;
  filterSeverities: Severity[] | null; // null means all
}

export interface ExportOptionsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onExport: (options: ExportOptions) => void;
  isExporting?: boolean;
}

const ExportOptionsModal: React.FC<ExportOptionsModalProps> = ({
  isOpen,
  onClose,
  onExport,
  isExporting = false
}) => {
  const [format, setFormat] = useState<'svg' | 'png'>('svg');
  const [resolution, setResolution] = useState<number>(1);
  const [includeLegend, setIncludeLegend] = useState(true);
  const [includeMetadata, setIncludeMetadata] = useState(true);
  const [filterType, setFilterType] = useState<string>('all');

  if (!isOpen) return null;

  const handleExport = () => {
    let filterSeverities: Severity[] | null = null;

    switch (filterType) {
      case 'critical':
        filterSeverities = ['critical'];
        break;
      case 'high-critical':
        filterSeverities = ['critical', 'high'];
        break;
      case 'medium-up':
        filterSeverities = ['critical', 'high', 'medium'];
        break;
      case 'all':
      default:
        filterSeverities = null;
        break;
    }

    onExport({
      format,
      resolution,
      includeLegend,
      includeMetadata,
      filterSeverities
    });
  };

  const resolutionLabels: Record<number, string> = {
    1: '1x (1920×1080)',
    2: '2x (3840×2160)',
    4: '4x (7680×4320)'
  };

  return (
    <>
      {/* Overlay */}
      <div
        className="fixed inset-0 bg-gray-900 bg-opacity-75 z-40"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="fixed inset-0 flex items-center justify-center z-50 p-4">
        <div className="bg-gray-800 border border-gray-700 rounded-lg shadow-xl max-w-md w-full">
          {/* Header */}
          <div className="px-6 py-4 border-b border-gray-700">
            <h2 className="text-xl font-semibold text-gray-100">
              Export Network Graph
            </h2>
          </div>

          {/* Body */}
          <div className="px-6 py-4 space-y-6">
            {/* Format Selection */}
            <div>
              <label className="block text-sm font-medium text-gray-200 mb-3">
                Export Format
              </label>
              <div className="space-y-2">
                <label className="flex items-center cursor-pointer">
                  <input
                    type="radio"
                    value="svg"
                    checked={format === 'svg'}
                    onChange={(e) => setFormat(e.target.value as 'svg')}
                    className="w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 focus:ring-blue-500"
                  />
                  <span className="ml-2 text-gray-200">
                    SVG (Vector - best for printing)
                  </span>
                </label>
                <label className="flex items-center cursor-pointer">
                  <input
                    type="radio"
                    value="png"
                    checked={format === 'png'}
                    onChange={(e) => setFormat(e.target.value as 'png')}
                    className="w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 focus:ring-blue-500"
                  />
                  <span className="ml-2 text-gray-200">
                    PNG (Raster - best for presentations)
                  </span>
                </label>
              </div>
            </div>

            {/* Resolution Slider (PNG only) */}
            {format === 'png' && (
              <div>
                <label className="block text-sm font-medium text-gray-200 mb-3">
                  PNG Resolution: {resolutionLabels[resolution]}
                </label>
                <input
                  type="range"
                  min="1"
                  max="4"
                  step="1"
                  value={resolution}
                  onChange={(e) => setResolution(parseInt(e.target.value))}
                  className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer slider"
                  list="resolution-marks"
                />
                <datalist id="resolution-marks">
                  <option value="1" label="1x" />
                  <option value="2" label="2x" />
                  <option value="4" label="4x" />
                </datalist>
                <div className="flex justify-between text-xs text-gray-400 mt-1">
                  <span>1x</span>
                  <span>2x</span>
                  <span>4x</span>
                </div>
              </div>
            )}

            {/* Filter Options */}
            <div>
              <label className="block text-sm font-medium text-gray-200 mb-3">
                Vulnerability Filter
              </label>
              <select
                value={filterType}
                onChange={(e) => setFilterType(e.target.value)}
                className="w-full bg-gray-700 border border-gray-600 text-gray-100 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Vulnerabilities</option>
                <option value="critical">Critical Only</option>
                <option value="high-critical">High + Critical</option>
                <option value="medium-up">Medium, High + Critical</option>
              </select>
            </div>

            {/* Include Options */}
            <div className="space-y-3">
              <label className="flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={includeLegend}
                  onChange={(e) => setIncludeLegend(e.target.checked)}
                  className="w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500"
                />
                <span className="ml-2 text-gray-200">Include Legend</span>
              </label>
              <label className="flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={includeMetadata}
                  onChange={(e) => setIncludeMetadata(e.target.checked)}
                  className="w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500"
                />
                <span className="ml-2 text-gray-200">
                  Include Metadata (timestamp, sources, filters)
                </span>
              </label>
            </div>
          </div>

          {/* Footer */}
          <div className="px-6 py-4 border-t border-gray-700 flex justify-end gap-3">
            <button
              onClick={onClose}
              disabled={isExporting}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-200 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Cancel
            </button>
            <button
              onClick={handleExport}
              disabled={isExporting}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isExporting ? (
                <>
                  <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Exporting...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  Export
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </>
  );
};

export default ExportOptionsModal;
