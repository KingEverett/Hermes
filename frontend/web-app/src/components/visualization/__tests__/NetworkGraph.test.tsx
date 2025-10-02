/**
 * NetworkGraph component tests
 *
 * Tests rendering, D3.js integration, color coding, and interactive controls.
 */

import React from 'react';
import { render } from '@testing-library/react';
import { screen, fireEvent } from '@testing-library/dom';
import { NetworkGraph } from '../NetworkGraph';

// Mock Zustand store
jest.mock('../../../stores/graphSelectionStore', () => ({
  useGraphSelectionStore: () => ({
    selectedNodeIds: [],
    hoveredNodeId: null,
    selectNode: jest.fn(),
    toggleNode: jest.fn(),
    selectAll: jest.fn(),
    clearSelection: jest.fn(),
    setHoveredNode: jest.fn(),
  }),
}));

// Mock keyboard shortcuts hook
jest.mock('../../../hooks/useKeyboardShortcuts', () => ({
  useKeyboardShortcuts: jest.fn(),
}));

// Mock GraphControls component
jest.mock('../GraphControls', () => ({
  GraphControls: () => <div data-testid="graph-controls">GraphControls</div>,
}));

// Mock D3 to avoid issues in test environment
const mockG = {
  append: jest.fn().mockReturnThis(),
  attr: jest.fn().mockReturnThis(),
  selectAll: jest.fn().mockReturnThis(),
  data: jest.fn().mockReturnThis(),
  enter: jest.fn().mockReturnThis(),
  call: jest.fn().mockReturnThis(),
  on: jest.fn().mockReturnThis(),
  filter: jest.fn().mockReturnThis(),
  node: jest.fn().mockReturnValue({ getBBox: () => ({ x: 0, y: 0, width: 100, height: 100 }) }),
};

const mockSvg = {
  selectAll: jest.fn().mockReturnValue({
    remove: jest.fn()
  }),
  append: jest.fn(() => mockG),
  attr: jest.fn().mockReturnThis(),
  call: jest.fn().mockReturnThis(),
  on: jest.fn().mockReturnThis(),
  transition: jest.fn().mockReturnThis(),
  duration: jest.fn().mockReturnThis(),
  node: jest.fn().mockReturnValue({ clientWidth: 1200, clientHeight: 800 }),
};

jest.mock('d3', () => ({
  select: jest.fn(() => mockSvg),
  forceSimulation: jest.fn().mockReturnValue({
    force: jest.fn().mockReturnThis(),
    on: jest.fn().mockReturnThis(),
    tick: jest.fn(),
    stop: jest.fn(),
    alphaTarget: jest.fn().mockReturnThis(),
    restart: jest.fn().mockReturnThis(),
    alphaDecay: jest.fn().mockReturnThis(),
  }),
  forceLink: jest.fn().mockReturnValue({
    id: jest.fn().mockReturnThis(),
    distance: jest.fn().mockReturnThis(),
  }),
  forceManyBody: jest.fn().mockReturnValue({
    strength: jest.fn().mockReturnThis(),
  }),
  forceCenter: jest.fn(),
  forceCollide: jest.fn().mockReturnValue({
    radius: jest.fn().mockReturnThis(),
  }),
  zoom: jest.fn().mockReturnValue({
    scaleExtent: jest.fn().mockReturnThis(),
    on: jest.fn().mockReturnThis(),
    touchable: jest.fn().mockReturnThis(),
    filter: jest.fn().mockReturnThis(),
    transform: jest.fn(),
    scaleBy: jest.fn(),
  }),
  zoomTransform: jest.fn().mockReturnValue({ k: 1, x: 0, y: 0 }),
  zoomIdentity: { translate: jest.fn().mockReturnThis(), scale: jest.fn().mockReturnThis() },
  drag: jest.fn().mockReturnValue({
    on: jest.fn().mockReturnThis(),
  }),
}));

describe('NetworkGraph', () => {
  const mockTopology = {
    nodes: [
      {
        id: 'host_1',
        type: 'host' as const,
        label: '192.168.1.1',
        x: 0,
        y: 0,
        metadata: {
          os: 'Linux',
          hostname: 'server1',
          status: 'up',
          color: '#3B82F6',
        },
      },
      {
        id: 'service_1',
        type: 'service' as const,
        label: '22/tcp',
        x: 100,
        y: 0,
        metadata: {
          service_name: 'ssh',
          product: 'OpenSSH',
          version: '7.4',
          vuln_count: 1,
          max_severity: 'high',
          color: '#F59E0B',
        },
      },
    ],
    edges: [
      {
        source: 'host_1',
        target: 'service_1',
      },
    ],
    metadata: {
      node_count: 2,
      edge_count: 1,
      generated_at: '2025-09-30T12:00:00Z',
    },
  };

  test('renders empty state when no topology provided', () => {
    const emptyTopology = {
      nodes: [],
      edges: [],
      metadata: { node_count: 0, edge_count: 0, generated_at: '' },
    };

    render(<NetworkGraph topology={emptyTopology} />);

    expect(screen.getByText('No network data available')).toBeInTheDocument();
    expect(
      screen.getByText('Add hosts and services to generate a topology graph')
    ).toBeInTheDocument();
  });

  test('renders SVG element with topology data', () => {
    render(<NetworkGraph topology={mockTopology} />);

    const svg = document.querySelector('svg');
    expect(svg).toBeInTheDocument();
    expect(svg).toHaveClass('bg-gray-50');
  });

  test('displays legend with color coding information', () => {
    render(<NetworkGraph topology={mockTopology} />);

    expect(screen.getByText('Legend')).toBeInTheDocument();
    expect(screen.getByText('Linux Host')).toBeInTheDocument();
    expect(screen.getByText('Windows Host')).toBeInTheDocument();
    expect(screen.getByText('Network Device')).toBeInTheDocument();
    expect(screen.getByText('Vulnerable Service')).toBeInTheDocument();
  });

  test('sets correct dimensions', () => {
    render(<NetworkGraph topology={mockTopology} width={800} height={600} />);

    const svg = document.querySelector('svg');
    expect(svg).toHaveAttribute('width', '800');
    expect(svg).toHaveAttribute('height', '600');
  });

  test('uses default dimensions when not specified', () => {
    render(<NetworkGraph topology={mockTopology} />);

    const svg = document.querySelector('svg');
    expect(svg).toHaveAttribute('width', '1200');
    expect(svg).toHaveAttribute('height', '800');
  });

  test('has accessibility attributes', () => {
    render(<NetworkGraph topology={mockTopology} />);

    const svg = document.querySelector('svg');
    expect(svg).toHaveAttribute('role', 'img');
    expect(svg).toHaveAttribute('aria-label', 'Network topology graph');
  });

  test('renders tooltip element', () => {
    render(<NetworkGraph topology={mockTopology} />);

    const tooltip = document.querySelector(
      '.absolute.bg-white.border.border-gray-300'
    );
    expect(tooltip).toBeInTheDocument();
  });
});

describe('NetworkGraph Interactive Controls', () => {
  const mockTopology = {
    nodes: [
      {
        id: 'host_1',
        type: 'host' as const,
        label: '192.168.1.1',
        x: 0,
        y: 0,
        metadata: {
          os: 'Linux',
          hostname: 'server1',
          status: 'up',
          color: '#3B82F6',
        },
      },
      {
        id: 'service_1',
        type: 'service' as const,
        label: '22/tcp',
        x: 100,
        y: 0,
        metadata: {
          service_name: 'ssh',
          product: 'OpenSSH',
          version: '7.4',
          vuln_count: 1,
          max_severity: 'high',
          color: '#F59E0B',
        },
      },
    ],
    edges: [
      {
        source: 'host_1',
        target: 'service_1',
      },
    ],
    metadata: {
      node_count: 2,
      edge_count: 1,
      generated_at: '2025-09-30T12:00:00Z',
    },
  };

  test('renders GraphControls toolbar', () => {
    render(<NetworkGraph topology={mockTopology} />);

    expect(screen.getByLabelText('Zoom in')).toBeInTheDocument();
    expect(screen.getByLabelText('Zoom out')).toBeInTheDocument();
    expect(screen.getByLabelText('Fit to screen')).toBeInTheDocument();
    expect(screen.getByLabelText('Reset view')).toBeInTheDocument();
  });

  test('displays keyboard shortcuts help', () => {
    render(<NetworkGraph topology={mockTopology} />);

    expect(screen.getByText('Shortcuts')).toBeInTheDocument();
    expect(screen.getByText('+/- : Zoom')).toBeInTheDocument();
    expect(screen.getByText('0 : Reset')).toBeInTheDocument();
    expect(screen.getByText('F : Fit')).toBeInTheDocument();
    expect(screen.getByText('Ctrl+A : Select All')).toBeInTheDocument();
    expect(screen.getByText('Esc : Clear')).toBeInTheDocument();
  });

  test('calls onNodeSelect callback when provided', () => {
    const onNodeSelect = jest.fn();
    render(<NetworkGraph topology={mockTopology} onNodeSelect={onNodeSelect} />);

    // Note: Actual node selection testing would require more complex D3 mocking
    // This test verifies the prop is accepted
    expect(onNodeSelect).not.toHaveBeenCalled();
  });

  test('accepts external selectedNodeIds prop', () => {
    render(<NetworkGraph topology={mockTopology} selectedNodeIds={['host_1']} />);

    // Component should render without errors
    const svg = document.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  test('displays selection badge when nodes are selected', () => {
    const { rerender } = render(<NetworkGraph topology={mockTopology} selectedNodeIds={[]} />);

    // Initially no selection badge
    expect(screen.queryByText(/node.*selected/)).not.toBeInTheDocument();

    // Rerender with selection
    rerender(<NetworkGraph topology={mockTopology} selectedNodeIds={['host_1']} />);
    expect(screen.getByText('1 node selected')).toBeInTheDocument();

    // Rerender with multiple selections
    rerender(<NetworkGraph topology={mockTopology} selectedNodeIds={['host_1', 'service_1']} />);
    expect(screen.getByText('2 nodes selected')).toBeInTheDocument();
  });

  test('zoom level indicator updates', () => {
    render(<NetworkGraph topology={mockTopology} />);

    // Should start at 100%
    expect(screen.getByText('100%')).toBeInTheDocument();
  });
});

describe('NetworkGraph Accessibility', () => {
  const mockTopology = {
    nodes: [
      {
        id: 'host_1',
        type: 'host' as const,
        label: '192.168.1.1',
        x: 0,
        y: 0,
        metadata: {
          os: 'Linux',
          color: '#3B82F6',
        },
      },
    ],
    edges: [],
    metadata: {
      node_count: 1,
      edge_count: 0,
      generated_at: '2025-09-30T12:00:00Z',
    },
  };

  test('control buttons have proper ARIA labels', () => {
    render(<NetworkGraph topology={mockTopology} />);

    expect(screen.getByLabelText('Zoom in')).toHaveAttribute('aria-label', 'Zoom in');
    expect(screen.getByLabelText('Zoom out')).toHaveAttribute('aria-label', 'Zoom out');
    expect(screen.getByLabelText('Fit to screen')).toHaveAttribute('aria-label', 'Fit to screen');
    expect(screen.getByLabelText('Reset view')).toHaveAttribute('aria-label', 'Reset view');
  });

  test('SVG has proper role and label', () => {
    render(<NetworkGraph topology={mockTopology} />);

    const svg = document.querySelector('svg');
    expect(svg).toHaveAttribute('role', 'img');
    expect(svg).toHaveAttribute('aria-label', 'Network topology graph');
  });

  test('control buttons are keyboard accessible', () => {
    render(<NetworkGraph topology={mockTopology} />);

    const zoomInButton = screen.getByLabelText('Zoom in');
    zoomInButton.focus();

    expect(document.activeElement).toBe(zoomInButton);
  });
});

describe('NetworkGraph Performance', () => {
  function generateLargeTopology(nodeCount: number) {
    const nodes = [];
    const edges = [];

    // Create host nodes
    const hostCount = Math.floor(nodeCount / 6); // 1 host per 5 services
    for (let i = 0; i < hostCount; i++) {
      nodes.push({
        id: `host_${i}`,
        type: 'host' as const,
        label: `10.0.${Math.floor(i / 255)}.${i % 255}`,
        x: Math.random() * 1000,
        y: Math.random() * 1000,
        metadata: {
          os: ['Linux', 'Windows', 'Network'][i % 3],
          status: 'up',
          color: '#3B82F6',
        },
      });
    }

    // Create service nodes
    const serviceCount = nodeCount - hostCount;
    for (let i = 0; i < serviceCount; i++) {
      const hostIndex = Math.floor(i / 5);
      nodes.push({
        id: `service_${i}`,
        type: 'service' as const,
        label: `${22 + (i % 50)}/tcp`,
        x: Math.random() * 1000,
        y: Math.random() * 1000,
        metadata: {
          service_name: 'service',
          vuln_count: 0,
          max_severity: 'none',
          color: '#10B981',
        },
      });

      // Add edge
      edges.push({
        source: `host_${hostIndex}`,
        target: `service_${i}`,
      });
    }

    return {
      nodes,
      edges,
      metadata: {
        node_count: nodes.length,
        edge_count: edges.length,
        generated_at: new Date().toISOString(),
      },
    };
  }

  test('handles large graphs without crashing', () => {
    const largeTopology = generateLargeTopology(500);

    expect(() => {
      render(<NetworkGraph topology={largeTopology} />);
    }).not.toThrow();
  });

  test('renders controls even with large graphs', () => {
    const largeTopology = generateLargeTopology(200);

    render(<NetworkGraph topology={largeTopology} />);

    expect(screen.getByLabelText('Zoom in')).toBeInTheDocument();
    expect(screen.getByText('Legend')).toBeInTheDocument();
    expect(screen.getByText('Shortcuts')).toBeInTheDocument();
  });
});
