/**
 * GraphLegend Component
 * Displays legend explaining graph symbols, colors, and statistics
 */

import React from 'react';

export interface GraphLegendProps {
  hostCount: number;
  serviceCount: number;
  vulnerabilityCounts: {
    critical: number;
    high: number;
    medium: number;
    low: number;
    info: number;
  };
  position?: 'bottom-center' | 'bottom-right' | 'top-right';
}

const GraphLegend: React.FC<GraphLegendProps> = ({
  hostCount,
  serviceCount,
  vulnerabilityCounts,
  position = 'bottom-center'
}) => {
  const totalVulns = Object.values(vulnerabilityCounts).reduce((sum, count) => sum + count, 0);

  const positionClasses = {
    'bottom-center': 'bottom-4 left-1/2 -translate-x-1/2',
    'bottom-right': 'bottom-4 right-4',
    'top-right': 'top-4 right-4'
  };

  return (
    <div
      className={`absolute ${positionClasses[position]} bg-gray-800 border border-gray-700 rounded-lg p-4 text-sm text-gray-100 shadow-lg`}
      style={{ minWidth: '300px' }}
    >
      <div className="font-semibold text-gray-100 mb-3 border-b border-gray-700 pb-2">
        Network Graph Legend
      </div>

      {/* Node Types */}
      <div className="mb-3">
        <div className="text-xs text-gray-400 uppercase tracking-wide mb-2">Node Types</div>
        <div className="space-y-1.5">
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 rounded-full bg-blue-500 border-2 border-blue-400"></div>
            <span>Host ({hostCount})</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 rounded-full bg-gray-500 border-2 border-gray-400"></div>
            <span>Service ({serviceCount})</span>
          </div>
        </div>
      </div>

      {/* Vulnerability Severity */}
      <div className="mb-3">
        <div className="text-xs text-gray-400 uppercase tracking-wide mb-2">
          Vulnerability Severity
        </div>
        <div className="space-y-1.5">
          {vulnerabilityCounts.critical > 0 && (
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-red-600"></div>
              <span>Critical ({vulnerabilityCounts.critical})</span>
            </div>
          )}
          {vulnerabilityCounts.high > 0 && (
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-orange-500"></div>
              <span>High ({vulnerabilityCounts.high})</span>
            </div>
          )}
          {vulnerabilityCounts.medium > 0 && (
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
              <span>Medium ({vulnerabilityCounts.medium})</span>
            </div>
          )}
          {vulnerabilityCounts.low > 0 && (
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-blue-400"></div>
              <span>Low ({vulnerabilityCounts.low})</span>
            </div>
          )}
          {vulnerabilityCounts.info > 0 && (
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-gray-400"></div>
              <span>Info ({vulnerabilityCounts.info})</span>
            </div>
          )}
        </div>
      </div>

      {/* Statistics */}
      <div className="pt-2 border-t border-gray-700">
        <div className="text-xs text-gray-400">
          Total: {hostCount} hosts, {serviceCount} services, {totalVulns} vulnerabilities
        </div>
      </div>
    </div>
  );
};

export default GraphLegend;

/**
 * Render GraphLegend as SVG element for export
 * @param props - Legend properties
 * @param width - SVG width
 * @param height - SVG height
 * @returns SVG group element
 */
export const renderLegendAsSVG = (
  props: GraphLegendProps,
  width: number,
  height: number
): SVGElement => {
  const { hostCount, serviceCount, vulnerabilityCounts } = props;
  const totalVulns = Object.values(vulnerabilityCounts).reduce((sum, count) => sum + count, 0);

  // Create legend group
  const legendGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
  legendGroup.setAttribute('id', 'graph-legend');

  // Position at bottom-center
  const legendWidth = 300;
  const legendHeight = 200;
  const x = (width - legendWidth) / 2;
  const y = height - legendHeight - 20;

  // Background rectangle
  const bgRect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
  bgRect.setAttribute('x', x.toString());
  bgRect.setAttribute('y', y.toString());
  bgRect.setAttribute('width', legendWidth.toString());
  bgRect.setAttribute('height', legendHeight.toString());
  bgRect.setAttribute('fill', '#1F2937');
  bgRect.setAttribute('stroke', '#374151');
  bgRect.setAttribute('stroke-width', '1');
  bgRect.setAttribute('rx', '8');
  legendGroup.appendChild(bgRect);

  let currentY = y + 25;

  // Title
  const title = createSVGText(x + 10, currentY, 'Network Graph Legend', '#F3F4F6', 14, 'bold');
  legendGroup.appendChild(title);
  currentY += 30;

  // Node types section
  const nodeTypesLabel = createSVGText(x + 10, currentY, 'NODE TYPES', '#9CA3AF', 10, 'normal');
  legendGroup.appendChild(nodeTypesLabel);
  currentY += 20;

  // Host node
  const hostCircle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
  hostCircle.setAttribute('cx', (x + 20).toString());
  hostCircle.setAttribute('cy', (currentY - 5).toString());
  hostCircle.setAttribute('r', '8');
  hostCircle.setAttribute('fill', '#3B82F6');
  hostCircle.setAttribute('stroke', '#60A5FA');
  hostCircle.setAttribute('stroke-width', '2');
  legendGroup.appendChild(hostCircle);
  const hostText = createSVGText(x + 35, currentY, `Host (${hostCount})`, '#D1D5DB', 12, 'normal');
  legendGroup.appendChild(hostText);
  currentY += 20;

  // Service node
  const serviceCircle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
  serviceCircle.setAttribute('cx', (x + 20).toString());
  serviceCircle.setAttribute('cy', (currentY - 5).toString());
  serviceCircle.setAttribute('r', '6');
  serviceCircle.setAttribute('fill', '#6B7280');
  serviceCircle.setAttribute('stroke', '#9CA3AF');
  serviceCircle.setAttribute('stroke-width', '2');
  legendGroup.appendChild(serviceCircle);
  const serviceText = createSVGText(x + 35, currentY, `Service (${serviceCount})`, '#D1D5DB', 12, 'normal');
  legendGroup.appendChild(serviceText);
  currentY += 30;

  // Vulnerability severity section
  const sevLabel = createSVGText(x + 10, currentY, 'VULNERABILITY SEVERITY', '#9CA3AF', 10, 'normal');
  legendGroup.appendChild(sevLabel);
  currentY += 20;

  const severities = [
    { name: 'Critical', color: '#DC2626', count: vulnerabilityCounts.critical },
    { name: 'High', color: '#F59E0B', count: vulnerabilityCounts.high },
    { name: 'Medium', color: '#EAB308', count: vulnerabilityCounts.medium },
    { name: 'Low', color: '#3B82F6', count: vulnerabilityCounts.low },
    { name: 'Info', color: '#6B7280', count: vulnerabilityCounts.info }
  ];

  severities.forEach(sev => {
    if (sev.count > 0) {
      const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      circle.setAttribute('cx', (x + 18).toString());
      circle.setAttribute('cy', (currentY - 4).toString());
      circle.setAttribute('r', '5');
      circle.setAttribute('fill', sev.color);
      legendGroup.appendChild(circle);

      const text = createSVGText(x + 35, currentY, `${sev.name} (${sev.count})`, '#D1D5DB', 12, 'normal');
      legendGroup.appendChild(text);
      currentY += 18;
    }
  });

  // Statistics footer
  currentY = y + legendHeight - 15;
  const statsText = createSVGText(
    x + 10,
    currentY,
    `Total: ${hostCount} hosts, ${serviceCount} services, ${totalVulns} vulnerabilities`,
    '#9CA3AF',
    10,
    'normal'
  );
  legendGroup.appendChild(statsText);

  return legendGroup;
};

/**
 * Helper to create SVG text element
 */
const createSVGText = (
  x: number,
  y: number,
  content: string,
  fill: string,
  fontSize: number,
  fontWeight: string
): SVGTextElement => {
  const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
  text.setAttribute('x', x.toString());
  text.setAttribute('y', y.toString());
  text.setAttribute('fill', fill);
  text.setAttribute('font-size', `${fontSize}px`);
  text.setAttribute('font-family', 'monospace');
  text.setAttribute('font-weight', fontWeight);
  text.textContent = content;
  return text;
};
