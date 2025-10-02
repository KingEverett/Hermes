/**
 * Graph Export Service
 * Provides SVG and PNG export functionality for network graphs
 */

export interface GraphMetadata {
  projectName: string;
  projectId: string;
  timestamp: Date;
  scanSources: string[];
  hostCount: number;
  serviceCount: number;
  vulnerabilityCount: number;
  appliedFilters?: FilterConfig;
  exportFormat: 'svg' | 'png';
  resolution?: number;
}

export interface FilterConfig {
  severities?: Severity[];
  hostIds?: string[];
  serviceTypes?: string[];
  showOnlyVulnerable?: boolean;
  label?: string;
}

export type Severity = 'critical' | 'high' | 'medium' | 'low' | 'info';

/**
 * Export SVG element to downloadable SVG file
 * @param svgElement - The SVG DOM element to export
 * @param filename - Desired filename for the download
 */
export const exportSVG = (svgElement: SVGElement, filename: string): void => {
  // Clone SVG to avoid modifying the displayed graph
  const clonedSvg = svgElement.cloneNode(true) as SVGElement;

  // Serialize SVG using browser-native XMLSerializer
  const serializer = new XMLSerializer();
  const svgString = serializer.serializeToString(clonedSvg);

  // Add XML declaration for standalone SVG file
  const svgBlob = new Blob(
    ['<?xml version="1.0" encoding="UTF-8"?>\n', svgString],
    { type: 'image/svg+xml;charset=utf-8' }
  );

  // Trigger browser download
  const url = URL.createObjectURL(svgBlob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};

/**
 * Export SVG element to downloadable PNG file with configurable resolution
 * @param svgElement - The SVG DOM element to export
 * @param resolution - Resolution multiplier (1x, 2x, 4x)
 * @param filename - Desired filename for the download
 * @returns Promise that resolves when export completes
 */
export const exportPNG = async (
  svgElement: SVGElement,
  resolution: number,
  filename: string
): Promise<void> => {
  return new Promise((resolve, reject) => {
    // Clone SVG to avoid modifying the displayed graph
    const clonedSvg = svgElement.cloneNode(true) as SVGElement;

    // Convert SVG to data URL
    const serializer = new XMLSerializer();
    const svgString = serializer.serializeToString(clonedSvg);

    // Use btoa for base64 encoding
    const svgDataUrl = `data:image/svg+xml;base64,${btoa(unescape(encodeURIComponent(svgString)))}`;

    // Create image element and load SVG
    const img = new Image();

    img.onload = () => {
      // Get SVG dimensions
      const baseWidth = svgElement.clientWidth || parseInt(svgElement.getAttribute('width') || '1000');
      const baseHeight = svgElement.clientHeight || parseInt(svgElement.getAttribute('height') || '800');

      // Create canvas with scaled dimensions
      const canvas = document.createElement('canvas');
      canvas.width = baseWidth * resolution;
      canvas.height = baseHeight * resolution;

      // Draw image to canvas
      const ctx = canvas.getContext('2d');
      if (!ctx) {
        reject(new Error('Failed to get canvas 2D context'));
        return;
      }

      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

      // Convert canvas to PNG blob
      canvas.toBlob((blob) => {
        if (!blob) {
          reject(new Error('Failed to create PNG blob'));
          return;
        }

        // Trigger download
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
        resolve();
      }, 'image/png');
    };

    img.onerror = () => reject(new Error('Failed to load SVG image'));
    img.src = svgDataUrl;
  });
};

/**
 * Generate standardized filename for graph export
 * @param projectName - Name of the project
 * @param format - Export format (svg or png)
 * @param filterLabel - Optional filter description
 * @returns Formatted filename
 */
export const generateExportFilename = (
  projectName: string,
  format: 'svg' | 'png',
  filterLabel?: string
): string => {
  const timestamp = new Date().toISOString().slice(0, 16).replace(/:/g, '-');
  const sanitizedProjectName = projectName.replace(/[^a-z0-9]/gi, '-').toLowerCase();
  const filterSuffix = filterLabel ? `-${filterLabel.replace(/[^a-z0-9]/gi, '-').toLowerCase()}` : '';

  return `${sanitizedProjectName}-network-graph${filterSuffix}-${timestamp}.${format}`;
};
