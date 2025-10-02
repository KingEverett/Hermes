/**
 * Graph Metadata Utility
 * Adds metadata overlays to SVG graphs for exports
 */

import { GraphMetadata } from '../services/graphExport';

/**
 * Add metadata overlay to SVG element
 * Renders project info, timestamp, scan sources, and filter info
 * @param svg - SVG element to add metadata to
 * @param metadata - Metadata information to display
 */
export const addMetadataOverlay = (
  svg: SVGElement,
  metadata: GraphMetadata
): void => {
  const width = parseInt(svg.getAttribute('width') || '1000');
  const height = parseInt(svg.getAttribute('height') || '800');

  // Create metadata group
  const metadataGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
  metadataGroup.setAttribute('id', 'export-metadata');

  // Top-left: Project name
  addTextWithBackground(
    metadataGroup,
    10,
    30,
    metadata.projectName,
    'start'
  );

  // Top-right: Timestamp
  const timestamp = `Exported: ${formatTimestamp(metadata.timestamp)}`;
  addTextWithBackground(
    metadataGroup,
    width - 10,
    30,
    timestamp,
    'end'
  );

  // Bottom-left: Scan sources
  if (metadata.scanSources.length > 0) {
    const sources = `Sources: ${metadata.scanSources.join(', ')}`;
    addTextWithBackground(
      metadataGroup,
      10,
      height - 10,
      sources,
      'start'
    );
  }

  // Bottom-right: Filter info (if applied)
  if (metadata.appliedFilters?.label) {
    addTextWithBackground(
      metadataGroup,
      width - 10,
      height - 10,
      metadata.appliedFilters.label,
      'end'
    );
  }

  svg.appendChild(metadataGroup);
};

/**
 * Add text element with semi-transparent background rectangle
 * @param parent - Parent SVG group element
 * @param x - X coordinate
 * @param y - Y coordinate
 * @param text - Text content
 * @param anchor - Text anchor alignment
 */
const addTextWithBackground = (
  parent: SVGElement,
  x: number,
  y: number,
  text: string,
  anchor: 'start' | 'middle' | 'end'
): void => {
  // Create text element
  const textElement = document.createElementNS('http://www.w3.org/2000/svg', 'text');
  textElement.setAttribute('x', x.toString());
  textElement.setAttribute('y', y.toString());
  textElement.setAttribute('fill', '#D1D5DB');
  textElement.setAttribute('font-size', '14px');
  textElement.setAttribute('font-family', 'monospace');
  textElement.setAttribute('text-anchor', anchor);
  textElement.textContent = text;

  // Temporarily append to get bounding box
  parent.appendChild(textElement);
  const bbox = textElement.getBBox();

  // Create background rectangle
  const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
  rect.setAttribute('x', (bbox.x - 5).toString());
  rect.setAttribute('y', (bbox.y - 2).toString());
  rect.setAttribute('width', (bbox.width + 10).toString());
  rect.setAttribute('height', (bbox.height + 4).toString());
  rect.setAttribute('fill', '#111827');
  rect.setAttribute('opacity', '0.7');
  rect.setAttribute('rx', '4');

  // Insert rectangle before text
  parent.insertBefore(rect, textElement);
};

/**
 * Format timestamp for display
 * @param date - Date to format
 * @returns Formatted timestamp string
 */
const formatTimestamp = (date: Date): string => {
  return date.toISOString().slice(0, 16).replace('T', ' ');
};

/**
 * Add statistics overlay to graph
 * Shows node and vulnerability counts
 * @param svg - SVG element
 * @param metadata - Metadata with statistics
 */
export const addStatisticsOverlay = (
  svg: SVGElement,
  metadata: GraphMetadata
): void => {
  const width = parseInt(svg.getAttribute('width') || '1000');

  // Create stats group
  const statsGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
  statsGroup.setAttribute('id', 'export-statistics');

  const stats = [
    `Hosts: ${metadata.hostCount}`,
    `Services: ${metadata.serviceCount}`,
    `Vulnerabilities: ${metadata.vulnerabilityCount}`
  ].join(' | ');

  addTextWithBackground(
    statsGroup,
    width / 2,
    30,
    stats,
    'middle'
  );

  svg.appendChild(statsGroup);
};
