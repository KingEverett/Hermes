/**
 * ExportButton Component
 * Button to trigger graph export modal
 * Integrates with GraphControls component
 */

import React, { useState } from 'react';
import ExportOptionsModal, { ExportOptions } from '../export/ExportOptionsModal';
import { exportSVG, exportPNG, generateExportFilename, GraphMetadata } from '../../services/graphExport';
import { addMetadataOverlay } from '../../utils/graphMetadata';
import { renderLegendAsSVG } from './GraphLegend';
import { getSeverityCounts } from '../../utils/graphFilter';

export interface ExportButtonProps {
  svgRef: React.RefObject<SVGSVGElement>;
  metadata: Omit<GraphMetadata, 'timestamp' | 'exportFormat' | 'resolution'>;
  onExportStart?: () => void;
  onExportComplete?: () => void;
  onExportError?: (error: Error) => void;
}

const ExportButton: React.FC<ExportButtonProps> = ({
  svgRef,
  metadata,
  onExportStart,
  onExportComplete,
  onExportError
}) => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  const handleExport = async (options: ExportOptions) => {
    if (!svgRef.current) {
      console.error('SVG ref is not available');
      return;
    }

    setIsExporting(true);
    onExportStart?.();

    try {
      // Clone SVG to avoid modifying the displayed graph
      const svgElement = svgRef.current;
      const clonedSvg = svgElement.cloneNode(true) as SVGElement;

      // Get SVG dimensions
      const width = parseInt(clonedSvg.getAttribute('width') || '1000');
      const height = parseInt(clonedSvg.getAttribute('height') || '800');

      // Add legend if requested
      if (options.includeLegend) {
        // Calculate severity counts from current graph
        // Note: In real implementation, this would come from the graph data
        const severityCounts = {
          critical: 0,
          high: 0,
          medium: 0,
          low: 0,
          info: 0
        };

        const legendSvg = renderLegendAsSVG(
          {
            hostCount: metadata.hostCount,
            serviceCount: metadata.serviceCount,
            vulnerabilityCounts: severityCounts
          },
          width,
          height
        );
        clonedSvg.appendChild(legendSvg);
      }

      // Add metadata overlay if requested
      if (options.includeMetadata) {
        const fullMetadata: GraphMetadata = {
          ...metadata,
          timestamp: new Date(),
          exportFormat: options.format,
          resolution: options.resolution,
          appliedFilters: options.filterSeverities
            ? {
                severities: options.filterSeverities,
                label: getFilterLabel(options.filterSeverities)
              }
            : undefined
        };

        addMetadataOverlay(clonedSvg, fullMetadata);
      }

      // Generate filename
      const filterLabel = options.filterSeverities
        ? getFilterLabel(options.filterSeverities)
        : undefined;
      const filename = generateExportFilename(
        metadata.projectName,
        options.format,
        filterLabel
      );

      // Export based on format
      if (options.format === 'svg') {
        exportSVG(clonedSvg, filename);
      } else {
        await exportPNG(clonedSvg, options.resolution, filename);
      }

      setIsModalOpen(false);
      onExportComplete?.();
    } catch (error) {
      console.error('Export failed:', error);
      onExportError?.(error as Error);
    } finally {
      setIsExporting(false);
    }
  };

  const getFilterLabel = (severities: string[]): string => {
    if (severities.length === 1) {
      return `${severities[0]}-only`;
    }
    if (severities.length === 2 && severities.includes('critical') && severities.includes('high')) {
      return 'high-critical';
    }
    if (severities.length === 3) {
      return 'medium-up';
    }
    return 'filtered';
  };

  return (
    <>
      <button
        onClick={() => setIsModalOpen(true)}
        className="px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors flex items-center gap-2"
        aria-label="Export Graph"
        title="Export Graph"
      >
        <svg
          className="h-5 w-5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
          />
        </svg>
        <span className="text-sm font-medium">Export</span>
      </button>

      <ExportOptionsModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onExport={handleExport}
        isExporting={isExporting}
      />
    </>
  );
};

export default ExportButton;
