/**
 * Smoke tests for AttackChainTree component
 *
 * DEV TEAM: Ensure React Query and Zustand store mocks are set up properly.
 * Goal: Verify tree renders and basic interactions work.
 */

import React from 'react';
import { render } from '@testing-library/react';
import { screen, fireEvent } from '@testing-library/dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import AttackChainTree from '../AttackChainTree';

const mockChains = [
  {
    id: 'chain-1',
    project_id: 'project-1',
    name: 'Web Server to DC',
    description: 'Initial foothold via SQL injection',
    color: '#FF6B35',
    node_count: 5,
    created_at: new Date(),
    updated_at: new Date(),
  },
  {
    id: 'chain-2',
    project_id: 'project-1',
    name: 'DMZ Pivot',
    description: 'Lateral movement',
    color: '#4ECDC4',
    node_count: 3,
    created_at: new Date(),
    updated_at: new Date(),
  },
];

const mockCallbacks = {
  onCreateChain: jest.fn(),
  onEditChain: jest.fn(),
  onExportChain: jest.fn(),
};

// Mock the hooks
jest.mock('../../../hooks/useAttackChains');
jest.mock('../../../stores/attackChainVisibilityStore');

describe('AttackChainTree', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });
    jest.clearAllMocks();

    // Setup mocks
    const useAttackChains = require('../../../hooks/useAttackChains');
    const useStore = require('../../../stores/attackChainVisibilityStore');

    useAttackChains.useProjectAttackChains = jest.fn(() => ({
      data: mockChains,
      isLoading: false,
    }));

    useAttackChains.useDeleteAttackChain = jest.fn(() => ({
      mutateAsync: jest.fn(),
    }));

    useStore.useAttackChainVisibilityStore = jest.fn(() => ({
      visibleChainIds: new Set(['chain-1']),
      activeChainId: null,
      toggleChainVisibility: jest.fn(),
      setActiveChain: jest.fn(),
    }));
  });

  const renderComponent = () => {
    return render(
      <QueryClientProvider client={queryClient}>
        <AttackChainTree projectId="project-1" {...mockCallbacks} />
      </QueryClientProvider>
    );
  };

  test('renders without crashing', () => {
    renderComponent();
    expect(screen.getByText('Attack Chains')).toBeInTheDocument();
  });

  test('displays all chains from the list', () => {
    renderComponent();
    expect(screen.getByText('Web Server to DC')).toBeInTheDocument();
    expect(screen.getByText('DMZ Pivot')).toBeInTheDocument();
  });

  test('shows create button', () => {
    renderComponent();
    const createButton = screen.getByText('+ New');
    expect(createButton).toBeInTheDocument();
  });

  test('calls onCreateChain when create button clicked', () => {
    renderComponent();
    const createButton = screen.getByText('+ New');
    fireEvent.click(createButton);
    expect(mockCallbacks.onCreateChain).toHaveBeenCalledTimes(1);
  });

  test('displays node count for each chain', () => {
    renderComponent();
    expect(screen.getByText('5 nodes')).toBeInTheDocument();
    expect(screen.getByText('3 nodes')).toBeInTheDocument();
  });

  test('shows visibility toggle icons', () => {
    renderComponent();
    // Should have eye icons for visibility toggle
    const eyeIcons = screen.getAllByRole('button', { name: /hide chain|show chain/i });
    expect(eyeIcons.length).toBeGreaterThan(0);
  });

  test('renders empty state when no chains', () => {
    // Mock empty data
    const useAttackChains = require('../../../hooks/useAttackChains');
    useAttackChains.useProjectAttackChains.mockReturnValue({
      data: [],
      isLoading: false,
    });

    renderComponent();
    expect(screen.getByText(/no attack chains yet/i)).toBeInTheDocument();
  });

  test('shows loading state', () => {
    const useAttackChains = require('../../../hooks/useAttackChains');
    useAttackChains.useProjectAttackChains.mockReturnValue({
      data: undefined,
      isLoading: true,
    });

    renderComponent();
    expect(screen.getByText(/loading attack chains/i)).toBeInTheDocument();
  });

  test('expands chain details when expand button clicked', () => {
    renderComponent();

    // Find the first expand button (▶ icon)
    const expandButtons = screen.getAllByRole('button');
    const firstExpandButton = expandButtons[0]; // First button should be expand/collapse

    fireEvent.click(firstExpandButton);

    // Should show description or node details
    expect(screen.getByText('Initial foothold via SQL injection')).toBeInTheDocument();
  });

  test('displays color indicator for each chain', () => {
    const { container } = renderComponent();

    // Should have colored dots
    const colorDots = container.querySelectorAll('div[style*="background-color"]');
    expect(colorDots.length).toBeGreaterThanOrEqual(2);
  });
});
