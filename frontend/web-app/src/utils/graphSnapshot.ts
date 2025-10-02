/**
 * Graph Snapshot Utility
 * Captures current graph state for export operations
 */

import { GraphMetadata, FilterConfig } from '../services/graphExport';

export interface GraphSnapshot {
  svg: SVGElement;
  metadata: GraphMetadata;
  timestamp: Date;
}

/**
 * Capture current graph snapshot for export
 * Clones SVG and resets transformations for clean export
 * @param svgRef - Reference to the SVG element
 * @param metadata - Graph metadata
 * @param appliedFilters - Currently applied filters (optional)
 * @returns Graph snapshot object
 */
export const captureGraphSnapshot = (
  svgRef: SVGElement,
  metadata: Omit<GraphMetadata, 'timestamp' | 'appliedFilters' | 'exportFormat'>,
  appliedFilters?: FilterConfig
): GraphSnapshot => {
  // Clone the SVG element to avoid modifying the displayed graph
  const clonedSvg = svgRef.cloneNode(true) as SVGElement;

  // Reset zoom/pan transformations for export
  // Find the main graph group (usually has transform attribute)
  const graphGroup = clonedSvg.querySelector('g[transform]');
  if (graphGroup) {
    // Reset to identity transform (show full graph, not zoomed view)
    graphGroup.removeAttribute('transform');
  }

  // Ensure SVG has proper dimensions set
  if (!clonedSvg.getAttribute('width')) {
    clonedSvg.setAttribute('width', svgRef.clientWidth.toString());
  }
  if (!clonedSvg.getAttribute('height')) {
    clonedSvg.setAttribute('height', svgRef.clientHeight.toString());
  }

  // Add viewBox if not present for proper scaling
  if (!clonedSvg.getAttribute('viewBox')) {
    const width = parseInt(clonedSvg.getAttribute('width') || '1000');
    const height = parseInt(clonedSvg.getAttribute('height') || '800');
    clonedSvg.setAttribute('viewBox', `0 0 ${width} ${height}`);
  }

  const timestamp = new Date();

  const fullMetadata: GraphMetadata = {
    ...metadata,
    timestamp,
    appliedFilters,
    exportFormat: 'svg' // Default, will be updated by export function
  };

  return {
    svg: clonedSvg,
    metadata: fullMetadata,
    timestamp
  };
};

/**
 * Prepare SVG for export by cleaning up unnecessary elements
 * @param svg - SVG element to clean
 * @returns Cleaned SVG element
 */
export const prepareSvgForExport = (svg: SVGElement): SVGElement => {
  const cleaned = svg.cloneNode(true) as SVGElement;

  // Remove any interactive overlays or UI elements
  const interactiveElements = cleaned.querySelectorAll('[data-interactive="true"]');
  interactiveElements.forEach(el => el.remove());

  // Remove any temporary highlights or selections
  const highlightElements = cleaned.querySelectorAll('.highlight, .selected, .hover');
  highlightElements.forEach(el => {
    el.classList.remove('highlight', 'selected', 'hover');
  });

  return cleaned;
};

/**
 * Calculate optimal SVG dimensions based on content
 * @param svg - SVG element
 * @returns Optimal width and height
 */
export const calculateOptimalDimensions = (svg: SVGGraphicsElement): { width: number; height: number } => {
  const bbox = svg.getBBox();
  const padding = 40; // Padding around content

  return {
    width: Math.ceil(bbox.width + bbox.x + padding),
    height: Math.ceil(bbox.height + bbox.y + padding)
  };
};
