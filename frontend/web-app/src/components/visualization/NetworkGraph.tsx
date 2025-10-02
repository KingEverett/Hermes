/**
 * NetworkGraph component
 *
 * D3.js-powered network topology visualization showing hosts, services,
 * and their relationships with color-coded vulnerability indicators.
 * Enhanced with zoom, pan, selection, keyboard shortcuts, and touch support.
 */

import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as d3 from 'd3';
import { useGraphSelectionStore } from '../../stores/graphSelectionStore';
import { useKeyboardShortcuts } from '../../hooks/useKeyboardShortcuts';
import { GraphControls } from './GraphControls';

// Type definitions matching backend models
interface GraphNode {
  id: string;
  type: 'host' | 'service';
  label: string;
  x?: number;
  y?: number;
  metadata: {
    os?: string;
    hostname?: string;
    status?: string;
    service_name?: string;
    product?: string;
    version?: string;
    vuln_count?: number;
    max_severity?: string;
    has_exploit?: boolean;
    color?: string;
  };
}

interface GraphEdge {
  source: string;
  target: string;
}

interface NetworkTopology {
  nodes: GraphNode[];
  edges: GraphEdge[];
  metadata: {
    node_count: number;
    edge_count: number;
    generated_at: string;
    layout_algorithm?: string;
  };
}

interface NetworkGraphProps {
  topology: NetworkTopology;
  width?: number;
  height?: number;
  onNodeSelect?: (nodeIds: string[]) => void;
  selectedNodeIds?: string[];
}

// D3 simulation node type with additional properties
interface D3Node extends GraphNode {
  x?: number;
  y?: number;
  fx?: number | null;
  fy?: number | null;
  vx?: number;
  vy?: number;
}

// D3 link type
interface D3Link extends d3.SimulationLinkDatum<D3Node> {
  source: string | D3Node;
  target: string | D3Node;
}

export const NetworkGraph: React.FC<NetworkGraphProps> = ({
  topology,
  width = 1200,
  height = 800,
  onNodeSelect,
  selectedNodeIds: externalSelectedNodeIds
}) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const zoomRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null);
  const gRef = useRef<d3.Selection<SVGGElement, unknown, null, undefined> | null>(null);
  const [currentZoomLevel, setCurrentZoomLevel] = useState(1);

  // Selection state from Zustand
  const {
    selectedNodeIds,
    selectNode,
    toggleNode,
    selectAll,
    clearSelection,
    setHoveredNode
  } = useGraphSelectionStore();

  // Use external selection if provided, otherwise use internal
  const activeSelection = externalSelectedNodeIds || selectedNodeIds;

  // Programmatic zoom functions
  const zoomIn = useCallback(() => {
    if (svgRef.current && zoomRef.current) {
      d3.select(svgRef.current)
        .transition()
        .duration(300)
        .call(zoomRef.current.scaleBy, 1.3);
    }
  }, []);

  const zoomOut = useCallback(() => {
    if (svgRef.current && zoomRef.current) {
      d3.select(svgRef.current)
        .transition()
        .duration(300)
        .call(zoomRef.current.scaleBy, 0.7);
    }
  }, []);

  const resetView = useCallback(() => {
    if (svgRef.current && zoomRef.current) {
      d3.select(svgRef.current)
        .transition()
        .duration(500)
        .call(zoomRef.current.transform, d3.zoomIdentity);
    }
  }, []);

  const fitToScreen = useCallback(() => {
    if (svgRef.current && zoomRef.current && gRef.current) {
      const g = gRef.current;
      const svg = d3.select(svgRef.current);
      const bounds = (g.node() as SVGGElement).getBBox();
      const fullWidth = svgRef.current.clientWidth;
      const fullHeight = svgRef.current.clientHeight;
      const graphWidth = bounds.width;
      const graphHeight = bounds.height;
      const midX = bounds.x + graphWidth / 2;
      const midY = bounds.y + graphHeight / 2;
      const scale = 0.9 / Math.max(graphWidth / fullWidth, graphHeight / fullHeight);
      const translate: [number, number] = [
        fullWidth / 2 - scale * midX,
        fullHeight / 2 - scale * midY
      ];

      svg
        .transition()
        .duration(750)
        .call(
          zoomRef.current.transform,
          d3.zoomIdentity.translate(translate[0], translate[1]).scale(scale)
        );
    }
  }, []);

  const handleSelectAll = useCallback(() => {
    if (topology && topology.nodes) {
      const allIds = topology.nodes.map(n => n.id);
      selectAll(allIds);
      if (onNodeSelect) {
        onNodeSelect(allIds);
      }
    }
  }, [topology, selectAll, onNodeSelect]);

  const handleClearSelection = useCallback(() => {
    clearSelection();
    if (onNodeSelect) {
      onNodeSelect([]);
    }
  }, [clearSelection, onNodeSelect]);

  // Keyboard shortcuts
  useKeyboardShortcuts({
    onZoomIn: zoomIn,
    onZoomOut: zoomOut,
    onReset: resetView,
    onFit: fitToScreen,
    onSelectAll: handleSelectAll,
    onClearSelection: handleClearSelection
  });

  useEffect(() => {
    if (!svgRef.current || !topology || topology.nodes.length === 0) {
      return;
    }

    // Clear existing content
    d3.select(svgRef.current).selectAll('*').remove();

    const svg = d3.select(svgRef.current);
    const g = svg.append('g');
    gRef.current = g;

    // Enhanced zoom behavior with smooth transitions and extended range
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 10])
      .touchable(true)
      .filter((event: any) => {
        // Allow zoom with mouse wheel, pinch, and touch
        return !event.ctrlKey || event.type === 'wheel';
      })
      .on('zoom', (event: any) => {
        g.attr('transform', event.transform);
        setCurrentZoomLevel(event.transform.k);
      });

    zoomRef.current = zoom;
    svg.call(zoom);

    // Double-click to zoom on node
    svg.on('dblclick.zoom', null); // Disable default double-click zoom

    // Click background to clear selection
    svg.on('click', (event: any) => {
      if (event.target === svg.node()) {
        handleClearSelection();
      }
    });

    // Convert nodes and links for D3 simulation
    const nodes: D3Node[] = topology.nodes.map(n => ({ ...n }));
    const links: D3Link[] = topology.edges.map(e => ({
      source: e.source,
      target: e.target
    }));

    // Create force simulation
    const simulation = d3.forceSimulation<D3Node>(nodes)
      .force('link', d3.forceLink<D3Node, D3Link>(links)
        .id((d: D3Node) => d.id)
        .distance(100))
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(30));

    // Optimize for large graphs
    if (nodes.length > 100) {
      simulation.alphaDecay(0.05); // Faster convergence
    }

    // Create links
    const link = g.append('g')
      .attr('class', 'links')
      .selectAll('line')
      .data(links)
      .enter().append('line')
      .attr('class', 'graph-link')
      .attr('stroke', '#9CA3AF')
      .attr('stroke-width', 2)
      .attr('stroke-opacity', 0.6);

    // Create nodes
    const node = g.append('g')
      .attr('class', 'nodes')
      .selectAll('g')
      .data(nodes)
      .enter().append('g')
      .attr('class', 'graph-node')
      .attr('data-node-id', (d: D3Node) => d.id)
      .call(d3.drag<SVGGElement, D3Node>()
        .on('start', dragStarted)
        .on('drag', dragged)
        .on('end', dragEnded));

    // Add SVG filter for glow effect on selected nodes
    const defs = svg.append('defs');
    const filter = defs.append('filter')
      .attr('id', 'glow')
      .attr('x', '-50%')
      .attr('y', '-50%')
      .attr('width', '200%')
      .attr('height', '200%');

    filter.append('feGaussianBlur')
      .attr('stdDeviation', '4')
      .attr('result', 'coloredBlur');

    const feMerge = filter.append('feMerge');
    feMerge.append('feMergeNode').attr('in', 'coloredBlur');
    feMerge.append('feMergeNode').attr('in', 'SourceGraphic');

    // Add circles for nodes
    node.append('circle')
      .attr('class', 'node-circle')
      .attr('r', (d: D3Node) => d.type === 'host' ? 20 : 15)
      .attr('fill', (d: D3Node) => d.metadata.color || '#9CA3AF')
      .attr('stroke', (d: D3Node) => {
        // Vulnerability border colors
        if (d.type === 'service' && d.metadata.vuln_count && d.metadata.vuln_count > 0) {
          return d.metadata.color || '#10B981';
        }
        return '#FFFFFF';
      })
      .attr('stroke-width', 2)
      .attr('data-id', (d: D3Node) => d.id);

    // Add labels
    node.append('text')
      .attr('class', 'node-label')
      .text((d: D3Node) => d.label)
      .attr('dy', (d: D3Node) => d.type === 'host' ? 30 : 25)
      .attr('text-anchor', 'middle')
      .attr('font-size', '12px')
      .attr('fill', '#1F2937')
      .attr('font-family', 'system-ui, -apple-system, sans-serif')
      .style('pointer-events', 'none');

    // Add vulnerability indicator icon for services
    node.filter((d: D3Node) => d.type === 'service' && d.metadata.vuln_count !== undefined && d.metadata.vuln_count > 0)
      .append('text')
      .text('⚠')
      .attr('dy', -20)
      .attr('text-anchor', 'middle')
      .attr('font-size', '16px')
      .attr('fill', (d: D3Node) => d.metadata.color || '#F59E0B')
      .style('pointer-events', 'none');

    // Node click handler with selection
    node.on('click', (event: any, d: D3Node) => {
      event.stopPropagation();

      if (event.ctrlKey || event.metaKey) {
        // Multi-select
        toggleNode(d.id);
        const newSelection = selectedNodeIds.includes(d.id)
          ? selectedNodeIds.filter((id: string) => id !== d.id)
          : [...selectedNodeIds, d.id];
        if (onNodeSelect) {
          onNodeSelect(newSelection);
        }
      } else {
        // Single select
        selectNode(d.id);
        if (onNodeSelect) {
          onNodeSelect([d.id]);
        }
      }
    });

    // Double-click to zoom on node
    node.on('dblclick', (event: any, d: D3Node) => {
      event.stopPropagation();
      if (d.x && d.y && svgRef.current) {
        const currentTransform = d3.zoomTransform(svgRef.current);
        const scale = Math.min(currentTransform.k * 1.5, 10);
        const translate: [number, number] = [
          width / 2 - scale * d.x,
          height / 2 - scale * d.y
        ];

        d3.select(svgRef.current)
          .transition()
          .duration(500)
          .call(
            zoom.transform,
            d3.zoomIdentity.translate(translate[0], translate[1]).scale(scale)
          );
      }
    });

    // Touch support - long press for selection
    let touchTimer: NodeJS.Timeout;
    node.on('touchstart', (event: any, d: D3Node) => {
      touchTimer = setTimeout(() => {
        selectNode(d.id);
        if (onNodeSelect) {
          onNodeSelect([d.id]);
        }
      }, 500);
    });

    node.on('touchend', () => {
      clearTimeout(touchTimer);
    });

    node.on('touchmove', () => {
      clearTimeout(touchTimer);
    });

    // Add tooltip on hover
    node.on('mouseenter', (event: any, d: D3Node) => {
      setHoveredNode(d.id);

      if (tooltipRef.current) {
        const tooltip = d3.select(tooltipRef.current);
        tooltip.style('opacity', 1);

        if (d.type === 'host') {
          tooltip.html(`
            <div class="font-semibold">${d.label}</div>
            ${d.metadata.hostname ? `<div>Hostname: ${d.metadata.hostname}</div>` : ''}
            ${d.metadata.os ? `<div>OS: ${d.metadata.os}</div>` : ''}
            <div>Status: ${d.metadata.status || 'unknown'}</div>
          `);
        } else {
          tooltip.html(`
            <div class="font-semibold">${d.label}</div>
            ${d.metadata.service_name ? `<div>Service: ${d.metadata.service_name}</div>` : ''}
            ${d.metadata.product ? `<div>Product: ${d.metadata.product}</div>` : ''}
            ${d.metadata.version ? `<div>Version: ${d.metadata.version}</div>` : ''}
            ${d.metadata.vuln_count ? `<div class="font-semibold text-red-600">Vulnerabilities: ${d.metadata.vuln_count}</div>` : ''}
            ${d.metadata.max_severity ? `<div>Severity: ${d.metadata.max_severity}</div>` : ''}
          `);
        }

        tooltip
          .style('left', `${event.pageX + 10}px`)
          .style('top', `${event.pageY - 10}px`);
      }
    })
    .on('mouseleave', () => {
      setHoveredNode(null);
      if (tooltipRef.current) {
        d3.select(tooltipRef.current).style('opacity', 0);
      }
    });

    // Update visual state based on selection
    const updateNodeStyles = () => {
      node.selectAll<SVGCircleElement, D3Node>('.node-circle')
        .attr('stroke', (d: D3Node) => {
          if (activeSelection.includes(d.id)) {
            return '#FBBF24'; // Yellow for selected
          }
          if (d.type === 'service' && d.metadata.vuln_count && d.metadata.vuln_count > 0) {
            return d.metadata.color || '#10B981';
          }
          return '#FFFFFF';
        })
        .attr('stroke-width', (d: D3Node) => activeSelection.includes(d.id) ? 3 : 2)
        .attr('filter', (d: D3Node) => activeSelection.includes(d.id) ? 'url(#glow)' : 'none');

      // Highlight connected edges
      link
        .attr('stroke', (d: D3Link) => {
          const sourceId = typeof d.source === 'object' ? d.source.id : d.source;
          const targetId = typeof d.target === 'object' ? d.target.id : d.target;
          return activeSelection.includes(sourceId) || activeSelection.includes(targetId)
            ? '#FBBF24'
            : '#9CA3AF';
        })
        .attr('stroke-width', (d: D3Link) => {
          const sourceId = typeof d.source === 'object' ? d.source.id : d.source;
          const targetId = typeof d.target === 'object' ? d.target.id : d.target;
          return activeSelection.includes(sourceId) || activeSelection.includes(targetId) ? 3 : 2;
        })
        .attr('stroke-opacity', (d: D3Link) => {
          const sourceId = typeof d.source === 'object' ? d.source.id : d.source;
          const targetId = typeof d.target === 'object' ? d.target.id : d.target;
          return activeSelection.includes(sourceId) || activeSelection.includes(targetId) ? 0.8 : 0.6;
        });
    };

    // Initial style update
    updateNodeStyles();

    // Update positions on simulation tick
    simulation.on('tick', () => {
      link
        .attr('x1', (d: D3Link) => (d.source as D3Node).x || 0)
        .attr('y1', (d: D3Link) => (d.source as D3Node).y || 0)
        .attr('x2', (d: D3Link) => (d.target as D3Node).x || 0)
        .attr('y2', (d: D3Link) => (d.target as D3Node).y || 0);

      node.attr('transform', (d: D3Node) => `translate(${d.x || 0},${d.y || 0})`);
    });

    // Drag functions
    function dragStarted(event: d3.D3DragEvent<SVGGElement, D3Node, D3Node>) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      event.subject.fx = event.subject.x;
      event.subject.fy = event.subject.y;
    }

    function dragged(event: d3.D3DragEvent<SVGGElement, D3Node, D3Node>) {
      event.subject.fx = event.x;
      event.subject.fy = event.y;
    }

    function dragEnded(event: d3.D3DragEvent<SVGGElement, D3Node, D3Node>) {
      if (!event.active) simulation.alphaTarget(0);
      event.subject.fx = null;
      event.subject.fy = null;
    }

    // Stop simulation after enough iterations for large graphs
    if (nodes.length > 100) {
      simulation.tick(300);
      simulation.stop();
    }

    // Cleanup
    return () => {
      simulation.stop();
    };
  }, [topology, width, height, activeSelection, onNodeSelect, selectNode, toggleNode, setHoveredNode, selectedNodeIds, handleClearSelection]);

  if (!topology || topology.nodes.length === 0) {
    return (
      <div className="flex items-center justify-center w-full h-full bg-gray-50">
        <div className="text-gray-500 text-center">
          <p className="text-lg font-semibold">No network data available</p>
          <p className="text-sm">Add hosts and services to generate a topology graph</p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative w-full h-full">
      <svg
        ref={svgRef}
        width={width}
        height={height}
        className="w-full h-full bg-gray-50"
        role="img"
        aria-label="Network topology graph"
      />

      {/* Graph Controls Toolbar */}
      <GraphControls
        onZoomIn={zoomIn}
        onZoomOut={zoomOut}
        onFitToScreen={fitToScreen}
        onReset={resetView}
        zoomLevel={currentZoomLevel}
      />

      {/* Selection Badge */}
      {activeSelection.length > 0 && (
        <div className="absolute top-4 left-4 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm shadow-lg">
          {activeSelection.length} node{activeSelection.length > 1 ? 's' : ''} selected
        </div>
      )}

      {/* Tooltip */}
      <div
        ref={tooltipRef}
        className="absolute bg-white border border-gray-300 rounded shadow-lg p-2 text-sm pointer-events-none opacity-0 transition-opacity z-10"
        style={{ maxWidth: '300px' }}
      />

      {/* Legend */}
      <div className="absolute bottom-4 right-4 bg-white border border-gray-300 rounded p-2 text-xs">
        <div className="font-semibold mb-1">Legend</div>
        <div className="flex items-center gap-2 mb-1">
          <div className="w-4 h-4 rounded-full bg-blue-500"></div>
          <span>Linux Host</span>
        </div>
        <div className="flex items-center gap-2 mb-1">
          <div className="w-4 h-4 rounded-full bg-purple-500"></div>
          <span>Windows Host</span>
        </div>
        <div className="flex items-center gap-2 mb-1">
          <div className="w-4 h-4 rounded-full bg-gray-500"></div>
          <span>Network Device</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-red-600 border-2 border-white"></div>
          <span>Vulnerable Service</span>
        </div>
      </div>

      {/* Keyboard Shortcuts Help */}
      <div className="absolute bottom-4 left-4 bg-white border border-gray-300 rounded p-2 text-xs">
        <div className="font-semibold mb-1">Shortcuts</div>
        <div>+/- : Zoom</div>
        <div>0 : Reset</div>
        <div>F : Fit</div>
        <div>Ctrl+A : Select All</div>
        <div>Esc : Clear</div>
      </div>
    </div>
  );
};

export default NetworkGraph;
