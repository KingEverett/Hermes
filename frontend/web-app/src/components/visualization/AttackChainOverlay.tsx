/**
 * Attack Chain Overlay Component
 *
 * Renders attack chain paths on top of the network graph using SVG
 */

import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import type { AttackChain } from '../../types/attackChain';
import { calculateChainCoordinates, generateChainPathData } from '../../utils/attackChainUtils';

interface GraphNode {
  id: string;
  x: number;
  y: number;
  [key: string]: any;
}

interface AttackChainOverlayProps {
  attackChain: AttackChain;
  nodes: GraphNode[];
  visible: boolean;
  isActive?: boolean;
  svgRef: React.RefObject<SVGSVGElement>;
}

const AttackChainOverlay: React.FC<AttackChainOverlayProps> = ({
  attackChain,
  nodes,
  visible,
  isActive = false,
  svgRef,
}) => {
  const groupRef = useRef<SVGGElement>(null);

  useEffect(() => {
    if (!svgRef.current || !groupRef.current || !visible || !attackChain.nodes.length) {
      return;
    }

    const svg = d3.select(svgRef.current);
    const g = d3.select(groupRef.current);

    // Clear previous rendering
    g.selectAll('*').remove();

    // Build node position map
    const nodePositions = new Map<string, { x: number; y: number }>();
    nodes.forEach((node) => {
      nodePositions.set(node.id, { x: node.x, y: node.y });
    });

    // Calculate chain coordinates
    const coordinates = calculateChainCoordinates(attackChain, nodePositions);

    if (coordinates.length === 0) {
      console.warn(`No coordinates found for chain ${attackChain.name}`);
      return;
    }

    // Generate path data
    const pathData = generateChainPathData(coordinates);

    // Draw the path
    const path = g
      .append('path')
      .attr('d', pathData)
      .attr('stroke', attackChain.color)
      .attr('stroke-width', isActive ? 5 : 3)
      .attr('stroke-dasharray', '5,5')
      .attr('fill', 'none')
      .attr('opacity', isActive ? 1.0 : 0.7)
      .attr('class', 'attack-chain-path');

    // Add marker for arrow
    const defs = svg.select('defs').empty() ? svg.append('defs') : svg.select('defs');

    defs
      .append('marker')
      .attr('id', `arrow-${attackChain.id}`)
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 8)
      .attr('refY', 0)
      .attr('markerWidth', 6)
      .attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', attackChain.color);

    path.attr('marker-end', `url(#arrow-${attackChain.id})`);

    // Animate dashed line
    const totalLength = (path.node() as SVGPathElement)?.getTotalLength() || 0;
    if (totalLength > 0) {
      path
        .attr('stroke-dashoffset', totalLength)
        .transition()
        .duration(2000)
        .ease(d3.easeLinear)
        .attr('stroke-dashoffset', 0);
    }

    // Draw sequence badges
    coordinates.forEach((coord, index) => {
      const badge = g
        .append('g')
        .attr('class', 'sequence-badge')
        .attr('transform', `translate(${coord.x},${coord.y})`);

      // Circle background
      badge
        .append('circle')
        .attr('r', 12)
        .attr('fill', '#FFFFFF')
        .attr('stroke', attackChain.color)
        .attr('stroke-width', 2);

      // Sequence number
      badge
        .append('text')
        .attr('text-anchor', 'middle')
        .attr('dy', '0.3em')
        .attr('fill', '#000000')
        .style('font-weight', 'bold')
        .style('font-size', '12px')
        .text(coord.node.sequence_order);

      // Add tooltip on hover
      if (coord.node.method_notes) {
        badge
          .append('title')
          .text(`Hop ${coord.node.sequence_order}: ${coord.node.method_notes}`);
      }

      // Draw branch indicators
      if (coord.node.is_branch_point && coord.node.branch_description) {
        const branchGroup = g
          .append('g')
          .attr('class', 'branch-indicator');

        // Dashed line for alternative path
        branchGroup
          .append('line')
          .attr('x1', coord.x)
          .attr('y1', coord.y)
          .attr('x2', coord.x + 50)
          .attr('y2', coord.y + 50)
          .attr('stroke', '#F7DC6F')
          .attr('stroke-width', 2)
          .attr('stroke-dasharray', '3,3');

        // Branch description text
        branchGroup
          .append('text')
          .attr('x', coord.x + 55)
          .attr('y', coord.y + 55)
          .attr('fill', '#F7DC6F')
          .style('font-size', '10px')
          .style('font-weight', 'bold')
          .text(coord.node.branch_description.substring(0, 30));
      }
    });

    // Add glow effect for active chain
    if (isActive) {
      const filter = defs
        .append('filter')
        .attr('id', `glow-${attackChain.id}`)
        .attr('x', '-50%')
        .attr('y', '-50%')
        .attr('width', '200%')
        .attr('height', '200%');

      filter
        .append('feGaussianBlur')
        .attr('stdDeviation', '3')
        .attr('result', 'coloredBlur');

      const feMerge = filter.append('feMerge');
      feMerge.append('feMergeNode').attr('in', 'coloredBlur');
      feMerge.append('feMergeNode').attr('in', 'SourceGraphic');

      path.attr('filter', `url(#glow-${attackChain.id})`);
    }

  }, [attackChain, nodes, visible, isActive, svgRef]);

  if (!visible) return null;

  return (
    <g
      ref={groupRef}
      className="attack-chain-overlay"
      data-chain-id={attackChain.id}
    />
  );
};

export default AttackChainOverlay;
