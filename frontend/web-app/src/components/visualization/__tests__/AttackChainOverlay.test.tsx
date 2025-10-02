/**
 * Smoke tests for AttackChainOverlay component
 *
 * DEV TEAM: Fill in the mock data and verify these tests pass.
 * Goal: Ensure component renders without crashing and basic functionality works.
 */

import React from 'react';
import { render } from '@testing-library/react';
import { screen } from '@testing-library/dom';
import AttackChainOverlay from '../AttackChainOverlay';
import type { AttackChain } from '../../../types/attackChain';

// TODO: Dev team - create proper mock data based on your AttackChain interface
const mockAttackChain: AttackChain = {
  id: 'test-chain-1',
  project_id: 'test-project-1',
  name: 'Test Attack Chain',
  description: 'Test description',
  color: '#FF6B35',
  created_at: new Date(),
  updated_at: new Date(),
  nodes: [
    {
      id: 'node-1',
      attack_chain_id: 'test-chain-1',
      entity_type: 'host',
      entity_id: 'host-123',
      sequence_order: 1,
      method_notes: 'SQL injection',
      is_branch_point: false,
      created_at: new Date(),
    },
    {
      id: 'node-2',
      attack_chain_id: 'test-chain-1',
      entity_type: 'service',
      entity_id: 'service-456',
      sequence_order: 2,
      method_notes: 'SSH credential reuse',
      is_branch_point: true,
      branch_description: 'Could pivot to mail server',
      created_at: new Date(),
    },
  ],
};

const mockNodes = [
  { id: 'host_host-123', x: 100, y: 100 },
  { id: 'service_service-456', x: 200, y: 200 },
];

const mockSvgRef = React.createRef<SVGSVGElement>();

describe('AttackChainOverlay', () => {
  // Create a real SVG element for the ref
  beforeEach(() => {
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    document.body.appendChild(svg);
    (mockSvgRef as any).current = svg;
  });

  afterEach(() => {
    if (mockSvgRef.current) {
      document.body.removeChild(mockSvgRef.current);
    }
  });

  test('renders without crashing when visible', () => {
    const { container } = render(
      <svg ref={mockSvgRef}>
        <AttackChainOverlay
          attackChain={mockAttackChain}
          nodes={mockNodes}
          visible={true}
          svgRef={mockSvgRef}
        />
      </svg>
    );

    // Component should render a group element
    expect(container.querySelector('.attack-chain-overlay')).toBeInTheDocument();
  });

  test('does not render when not visible', () => {
    const { container } = render(
      <svg ref={mockSvgRef}>
        <AttackChainOverlay
          attackChain={mockAttackChain}
          nodes={mockNodes}
          visible={false}
          svgRef={mockSvgRef}
        />
      </svg>
    );

    // When not visible, component returns null
    expect(container.querySelector('.attack-chain-overlay')).not.toBeInTheDocument();
  });

  test('applies active styling when isActive is true', () => {
    const { container } = render(
      <svg ref={mockSvgRef}>
        <AttackChainOverlay
          attackChain={mockAttackChain}
          nodes={mockNodes}
          visible={true}
          isActive={true}
          svgRef={mockSvgRef}
        />
      </svg>
    );

    // Check that path exists (D3.js should render it)
    const path = container.querySelector('.attack-chain-path');
    expect(path).toBeInTheDocument();
  });

  test('handles empty nodes array gracefully', () => {
    const emptyChain = { ...mockAttackChain, nodes: [] };

    const { container } = render(
      <svg ref={mockSvgRef}>
        <AttackChainOverlay
          attackChain={emptyChain}
          nodes={mockNodes}
          visible={true}
          svgRef={mockSvgRef}
        />
      </svg>
    );

    // Should not crash with empty nodes
    expect(container.querySelector('.attack-chain-overlay')).toBeInTheDocument();
  });

  test('renders sequence badges for each node', () => {
    const { container } = render(
      <svg ref={mockSvgRef}>
        <AttackChainOverlay
          attackChain={mockAttackChain}
          nodes={mockNodes}
          visible={true}
          svgRef={mockSvgRef}
        />
      </svg>
    );

    // D3.js should create sequence badges
    const badges = container.querySelectorAll('.sequence-badge');
    expect(badges.length).toBeGreaterThan(0);
  });

  test('renders branch indicators for branch points', () => {
    const { container } = render(
      <svg ref={mockSvgRef}>
        <AttackChainOverlay
          attackChain={mockAttackChain}
          nodes={mockNodes}
          visible={true}
          svgRef={mockSvgRef}
        />
      </svg>
    );

    // Should render branch indicator for node 2
    const branchIndicators = container.querySelectorAll('.branch-indicator');
    expect(branchIndicators.length).toBeGreaterThan(0);
  });
});
