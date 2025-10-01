/**
 * Mock data and utilities for Attack Chain testing
 *
 * DEV TEAM: Use these mocks in your tests to maintain consistency.
 * Add more mock data as needed for different test scenarios.
 */

import type { AttackChain, AttackChainNode, AttackChainListItem } from '../types/attackChain';

export const mockAttackChainNode: AttackChainNode = {
  id: 'node-1',
  attack_chain_id: 'chain-1',
  entity_type: 'host',
  entity_id: 'host-123',
  sequence_order: 1,
  method_notes: 'SQL injection in login form',
  is_branch_point: false,
  created_at: new Date('2025-01-01T00:00:00Z'),
};

export const mockBranchPointNode: AttackChainNode = {
  id: 'node-2',
  attack_chain_id: 'chain-1',
  entity_type: 'service',
  entity_id: 'service-456',
  sequence_order: 2,
  method_notes: 'SSH credential reuse',
  is_branch_point: true,
  branch_description: 'Could pivot to 10.0.0.51 (Mail Server) with same credentials',
  created_at: new Date('2025-01-01T00:00:00Z'),
};

export const mockAttackChain: AttackChain = {
  id: 'chain-1',
  project_id: 'project-1',
  name: 'Web Server to Domain Controller',
  description: 'Exploited vulnerable web service to gain initial foothold',
  color: '#FF6B35',
  created_at: new Date('2025-01-01T00:00:00Z'),
  updated_at: new Date('2025-01-01T00:00:00Z'),
  nodes: [mockAttackChainNode, mockBranchPointNode],
};

export const mockAttackChainListItem: AttackChainListItem = {
  id: 'chain-1',
  project_id: 'project-1',
  name: 'Web Server to Domain Controller',
  description: 'Exploited vulnerable web service to gain initial foothold',
  color: '#FF6B35',
  node_count: 2,
  created_at: new Date('2025-01-01T00:00:00Z'),
  updated_at: new Date('2025-01-01T00:00:00Z'),
};

export const mockChains: AttackChainListItem[] = [
  mockAttackChainListItem,
  {
    id: 'chain-2',
    project_id: 'project-1',
    name: 'DMZ Pivot',
    description: 'Lateral movement through DMZ',
    color: '#4ECDC4',
    node_count: 3,
    created_at: new Date('2025-01-01T00:00:00Z'),
    updated_at: new Date('2025-01-01T00:00:00Z'),
  },
];

export const mockGraphNodes = [
  { id: 'host_host-123', x: 100, y: 100, type: 'host' as const },
  { id: 'service_service-456', x: 200, y: 200, type: 'service' as const },
  { id: 'host_host-789', x: 300, y: 300, type: 'host' as const },
];

export const mockGraphEdges = [
  { source: 'host_host-123', target: 'service_service-456' },
  { source: 'service_service-456', target: 'host_host-789' },
];

/**
 * Creates a mock SVG ref for testing components that use D3.js
 */
export const createMockSvgRef = () => {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  document.body.appendChild(svg);
  return { current: svg };
};

/**
 * Cleanup mock SVG ref after tests
 */
export const cleanupMockSvgRef = (ref: { current: SVGSVGElement | null }) => {
  if (ref.current && document.body.contains(ref.current)) {
    document.body.removeChild(ref.current);
  }
};
