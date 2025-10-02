/**
 * Utility functions for attack chain path calculation and validation
 */

import type { AttackChain, AttackChainNode } from '../types/attackChain';

export interface GraphNode {
  id: string;
  x: number;
  y: number;
  type: 'host' | 'service';
  [key: string]: any;
}

export interface GraphEdge {
  source: string;
  target: string;
  [key: string]: any;
}

export interface ValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

export interface ChainCoordinate {
  x: number;
  y: number;
  node: AttackChainNode;
}

/**
 * Validate that an attack chain path is valid based on graph topology
 */
export const validateChainPath = (
  nodes: AttackChainNode[],
  graphEdges: GraphEdge[]
): ValidationResult => {
  const errors: string[] = [];
  const warnings: string[] = [];

  if (nodes.length === 0) {
    return { valid: true, errors, warnings };
  }

  // Sort nodes by sequence order
  const sortedNodes = [...nodes].sort((a, b) => a.sequence_order - b.sequence_order);

  // Check each hop has a valid connection
  for (let i = 0; i < sortedNodes.length - 1; i++) {
    const currentNode = sortedNodes[i];
    const nextNode = sortedNodes[i + 1];

    const currentId = `${currentNode.entity_type}_${currentNode.entity_id}`;
    const nextId = `${nextNode.entity_type}_${nextNode.entity_id}`;

    // Look for direct edge connection
    const hasDirectEdge = graphEdges.some(
      (edge) =>
        (edge.source === currentId && edge.target === nextId) ||
        (edge.target === currentId && edge.source === nextId)
    );

    if (!hasDirectEdge) {
      // For host-to-host connections, check if there's an intermediate service
      if (currentNode.entity_type === 'host' && nextNode.entity_type === 'host') {
        warnings.push(
          `No direct connection found between hop ${currentNode.sequence_order} and ${nextNode.sequence_order}. ` +
          `Intermediate service connections may exist.`
        );
      } else {
        errors.push(
          `Invalid path: No connection between hop ${currentNode.sequence_order} ` +
          `(${currentNode.entity_type}) and hop ${nextNode.sequence_order} (${nextNode.entity_type})`
        );
      }
    }
  }

  // Check for duplicate sequence orders
  const sequenceOrders = sortedNodes.map((n) => n.sequence_order);
  const uniqueOrders = new Set(sequenceOrders);
  if (sequenceOrders.length !== uniqueOrders.size) {
    errors.push('Duplicate sequence orders detected');
  }

  return {
    valid: errors.length === 0,
    errors,
    warnings,
  };
};

/**
 * Calculate coordinates for rendering attack chain path
 */
export const calculateChainCoordinates = (
  chain: AttackChain,
  nodePositions: Map<string, { x: number; y: number }>
): ChainCoordinate[] => {
  if (!chain.nodes || chain.nodes.length === 0) {
    return [];
  }

  // Sort nodes by sequence order
  const sortedNodes = [...chain.nodes].sort(
    (a, b) => a.sequence_order - b.sequence_order
  );

  // Map each node to its coordinates
  return sortedNodes
    .map((node) => {
      const nodeId = `${node.entity_type}_${node.entity_id}`;
      const position = nodePositions.get(nodeId);

      if (!position) {
        console.warn(`No position found for node ${nodeId} in chain ${chain.name}`);
        return null;
      }

      return {
        x: position.x,
        y: position.y,
        node,
      };
    })
    .filter((coord): coord is ChainCoordinate => coord !== null);
};

/**
 * Generate SVG path data for attack chain visualization
 */
export const generateChainPathData = (coordinates: ChainCoordinate[]): string => {
  if (coordinates.length === 0) return '';

  const pathParts: string[] = [];

  // Move to first point
  pathParts.push(`M ${coordinates[0].x} ${coordinates[0].y}`);

  // Draw curves through remaining points using quadratic bezier curves
  for (let i = 1; i < coordinates.length; i++) {
    const curr = coordinates[i];
    const prev = coordinates[i - 1];

    // Calculate control point for smooth curve
    const controlX = (prev.x + curr.x) / 2;
    const controlY = (prev.y + curr.y) / 2;

    // Use quadratic bezier curve
    pathParts.push(`Q ${controlX} ${controlY} ${curr.x} ${curr.y}`);
  }

  return pathParts.join(' ');
};

/**
 * Get node by entity type and ID from graph
 */
export const getGraphNode = (
  graphNodes: GraphNode[],
  entityType: string,
  entityId: string
): GraphNode | undefined => {
  const nodeId = `${entityType}_${entityId}`;
  return graphNodes.find((node) => node.id === nodeId);
};

/**
 * Check if two nodes are connected in the graph
 */
export const areNodesConnected = (
  sourceId: string,
  targetId: string,
  graphEdges: GraphEdge[]
): boolean => {
  return graphEdges.some(
    (edge) =>
      (edge.source === sourceId && edge.target === targetId) ||
      (edge.target === sourceId && edge.source === targetId)
  );
};

/**
 * Find the next visible chain in the list (for keyboard navigation)
 */
export const getNextVisibleChain = (
  currentChainId: string | null,
  visibleChainIds: Set<string>,
  allChains: { id: string }[]
): string | null => {
  const visibleChains = allChains.filter((chain) => visibleChainIds.has(chain.id));

  if (visibleChains.length === 0) return null;
  if (visibleChains.length === 1) return visibleChains[0].id;

  if (!currentChainId) return visibleChains[0].id;

  const currentIndex = visibleChains.findIndex((chain) => chain.id === currentChainId);
  if (currentIndex === -1) return visibleChains[0].id;

  const nextIndex = (currentIndex + 1) % visibleChains.length;
  return visibleChains[nextIndex].id;
};

/**
 * Find the previous visible chain in the list (for keyboard navigation)
 */
export const getPreviousVisibleChain = (
  currentChainId: string | null,
  visibleChainIds: Set<string>,
  allChains: { id: string }[]
): string | null => {
  const visibleChains = allChains.filter((chain) => visibleChainIds.has(chain.id));

  if (visibleChains.length === 0) return null;
  if (visibleChains.length === 1) return visibleChains[0].id;

  if (!currentChainId) return visibleChains[visibleChains.length - 1].id;

  const currentIndex = visibleChains.findIndex((chain) => chain.id === currentChainId);
  if (currentIndex === -1) return visibleChains[visibleChains.length - 1].id;

  const prevIndex = (currentIndex - 1 + visibleChains.length) % visibleChains.length;
  return visibleChains[prevIndex].id;
};
