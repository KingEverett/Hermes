/**
 * Tests for AttackChainEditor component
 *
 * Verifies editing, reordering, node addition/removal, and validation
 */

import React from 'react';
import { render } from '@testing-library/react';
import { screen, fireEvent, waitFor } from '@testing-library/dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import AttackChainEditor from '../AttackChainEditor';
import { AttackChain } from '../../../types/attackChain';

// Mock the hooks
jest.mock('../../../hooks/useAttackChains');

const mockChain: AttackChain = {
  id: 'chain-1',
  project_id: 'project-1',
  name: 'Test Chain',
  description: 'Test description',
  color: '#FF6B35',
  created_at: new Date('2025-01-01'),
  updated_at: new Date('2025-01-01'),
  nodes: [
    {
      id: 'node-1',
      attack_chain_id: 'chain-1',
      entity_type: 'host',
      entity_id: 'host-1',
      sequence_order: 1,
      method_notes: 'SQL injection',
      is_branch_point: false,
      created_at: new Date('2025-01-01'),
    },
    {
      id: 'node-2',
      attack_chain_id: 'chain-1',
      entity_type: 'service',
      entity_id: 'svc-1',
      sequence_order: 2,
      method_notes: 'Credential reuse',
      is_branch_point: true,
      branch_description: 'Alternative path via mail server',
      created_at: new Date('2025-01-01'),
    },
  ],
};

const mockProps = {
  chainId: 'chain-1',
  projectId: 'project-1',
  isOpen: true,
  onClose: jest.fn(),
  onSave: jest.fn(),
  onNodeSelect: jest.fn(),
};

describe('AttackChainEditor', () => {
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
    useAttackChains.useAttackChain = jest.fn(() => ({
      data: mockChain,
      isLoading: false,
      error: null,
    }));
    useAttackChains.useUpdateAttackChain = jest.fn(() => ({
      mutateAsync: jest.fn().mockResolvedValue(mockChain),
      isPending: false,
    }));
  });

  const renderComponent = (props = mockProps) => {
    return render(
      <QueryClientProvider client={queryClient}>
        <AttackChainEditor {...props} />
      </QueryClientProvider>
    );
  };

  test('renders loading state', () => {
    const useAttackChains = require('../../../hooks/useAttackChains');
    useAttackChains.useAttackChain = jest.fn(() => ({
      data: null,
      isLoading: true,
      error: null,
    }));

    renderComponent();
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  test('renders error state', () => {
    const useAttackChains = require('../../../hooks/useAttackChains');
    useAttackChains.useAttackChain = jest.fn(() => ({
      data: null,
      isLoading: false,
      error: new Error('Failed to load'),
    }));

    renderComponent();
    expect(screen.getByText(/error loading chain/i)).toBeInTheDocument();
  });

  test('loads existing chain data correctly', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByDisplayValue('Test Chain')).toBeInTheDocument();
      expect(screen.getByDisplayValue('Test description')).toBeInTheDocument();
      expect(screen.getByText('#FF6B35')).toBeInTheDocument();
    });
  });

  test('displays chain nodes in order', async () => {
    renderComponent();

    await waitFor(() => {
      const nodeItems = screen.getAllByText(/host|service/i);
      expect(nodeItems.length).toBeGreaterThan(0);
    });
  });

  test('updates chain name', async () => {
    renderComponent();

    const nameInput = await screen.findByDisplayValue('Test Chain');
    fireEvent.change(nameInput, { target: { value: 'Updated Chain Name' } });

    expect(nameInput).toHaveValue('Updated Chain Name');
  });

  test('updates chain description', async () => {
    renderComponent();

    const descInput = await screen.findByDisplayValue('Test description');
    fireEvent.change(descInput, { target: { value: 'New description' } });

    expect(descInput).toHaveValue('New description');
  });

  test('updates chain color', async () => {
    renderComponent();

    // Color input is type="color", need to query differently
    const colorInputs = await screen.findAllByRole('textbox');
    const colorInput = document.querySelector('input[type="color"]') as HTMLInputElement;
    expect(colorInput).toBeTruthy();

    fireEvent.change(colorInput, { target: { value: '#00ff00' } });

    expect(colorInput).toHaveValue('#00ff00');
  });

  test('shows validation error for short name', async () => {
    renderComponent();

    const nameInput = await screen.findByDisplayValue('Test Chain');
    fireEvent.change(nameInput, { target: { value: 'AB' } });

    const saveButton = screen.getByText(/save changes/i);
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(screen.getByText(/at least 3 characters/i)).toBeInTheDocument();
    });
  });

  test('shows validation error for invalid color', async () => {
    renderComponent();

    const colorInput = document.querySelector('input[type="color"]') as HTMLInputElement;
    expect(colorInput).toBeTruthy();

    // Manually set invalid value bypassing HTML5 normalization
    Object.defineProperty(colorInput, 'value', {
      writable: true,
      value: 'invalid',
    });
    fireEvent.change(colorInput, { target: { value: 'invalid' } });

    const saveButton = screen.getByText(/save changes/i);
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(screen.getByText(/invalid color format/i)).toBeInTheDocument();
    });
  });

  test('expands and collapses node details', async () => {
    renderComponent();

    await waitFor(() => {
      const expandButtons = screen.getAllByText('▶');
      expect(expandButtons.length).toBeGreaterThan(0);
    });

    const expandButtons = screen.getAllByText('▶');
    fireEvent.click(expandButtons[0]);

    await waitFor(() => {
      expect(screen.getByText(/exploitation method/i)).toBeInTheDocument();
    });
  });

  test('updates method notes when node is expanded', async () => {
    renderComponent();

    // Expand first node
    const expandButtons = screen.getAllByText('▶');
    fireEvent.click(expandButtons[0]);

    await waitFor(() => {
      const methodInput = screen.getByDisplayValue('SQL injection');
      fireEvent.change(methodInput, { target: { value: 'Updated method' } });
      expect(methodInput).toHaveValue('Updated method');
    });
  });

  test('toggles branch point checkbox', async () => {
    renderComponent();

    // Expand first node
    const expandButtons = screen.getAllByText('▶');
    fireEvent.click(expandButtons[0]);

    await waitFor(() => {
      const checkbox = screen.getByLabelText(/mark as branch point/i);
      fireEvent.click(checkbox);
      expect(checkbox).toBeChecked();
    });
  });

  test('shows branch description field when branch point is checked', async () => {
    renderComponent();

    // Expand second node (which has is_branch_point: true)
    const expandButtons = screen.getAllByText('▶');
    fireEvent.click(expandButtons[1]);

    await waitFor(() => {
      expect(screen.getByDisplayValue('Alternative path via mail server')).toBeInTheDocument();
    });
  });

  test('shows add node button', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText(/\+ add node/i)).toBeInTheDocument();
    });
  });

  test('enters selection mode when add node clicked', async () => {
    renderComponent();

    const addButton = await screen.findByText(/\+ add node/i);
    fireEvent.click(addButton);

    await waitFor(() => {
      expect(screen.getByText(/click a node on the graph/i)).toBeInTheDocument();
      expect(screen.getByText(/cancel selection/i)).toBeInTheDocument();
    });
  });

  test('exits selection mode when cancel clicked', async () => {
    renderComponent();

    const addButton = await screen.findByText(/\+ add node/i);
    fireEvent.click(addButton);

    const cancelButton = await screen.findByText(/cancel selection/i);
    fireEvent.click(cancelButton);

    await waitFor(() => {
      expect(screen.queryByText(/cancel selection/i)).not.toBeInTheDocument();
      expect(screen.getByText(/\+ add node/i)).toBeInTheDocument();
    });
  });

  test('shows delete button for each node', async () => {
    renderComponent();

    await waitFor(() => {
      // Should have 2 delete buttons (one per node)
      const deleteButtons = screen.getAllByTitle(/remove node/i);
      expect(deleteButtons).toHaveLength(2);
    });
  });

  test('prevents removing last node', async () => {
    // Mock chain with only one node
    const useAttackChains = require('../../../hooks/useAttackChains');
    useAttackChains.useAttackChain = jest.fn(() => ({
      data: {
        ...mockChain,
        nodes: [mockChain.nodes[0]],
      },
      isLoading: false,
      error: null,
    }));

    // Mock window.alert
    const alertMock = jest.spyOn(window, 'alert').mockImplementation(() => {});

    renderComponent();

    await waitFor(() => {
      const deleteButtons = screen.getAllByTitle(/remove node/i);
      fireEvent.click(deleteButtons[0]);
    });

    expect(alertMock).toHaveBeenCalledWith(
      expect.stringContaining('Cannot remove the last node')
    );

    alertMock.mockRestore();
  });

  test('shows confirmation before deleting node', async () => {
    const confirmMock = jest.spyOn(window, 'confirm').mockReturnValue(false);

    renderComponent();

    await waitFor(() => {
      const deleteButtons = screen.getAllByTitle(/remove node/i);
      fireEvent.click(deleteButtons[0]);
    });

    expect(confirmMock).toHaveBeenCalledWith(
      expect.stringContaining('Remove this node')
    );

    confirmMock.mockRestore();
  });

  test('removes node after confirmation', async () => {
    const confirmMock = jest.spyOn(window, 'confirm').mockReturnValue(true);

    renderComponent();

    await waitFor(() => {
      const deleteButtons = screen.getAllByTitle(/remove node/i);
      expect(deleteButtons).toHaveLength(2);
    });

    const deleteButtons = screen.getAllByTitle(/remove node/i);
    fireEvent.click(deleteButtons[0]);

    await waitFor(() => {
      // Should now have 1 delete button
      const remainingButtons = screen.getAllByTitle(/remove node/i);
      expect(remainingButtons).toHaveLength(1);
    });

    confirmMock.mockRestore();
  });

  test('calls API with correct payload on save', async () => {
    const useAttackChains = require('../../../hooks/useAttackChains');
    const mockMutate = jest.fn().mockResolvedValue(mockChain);
    useAttackChains.useUpdateAttackChain = jest.fn(() => ({
      mutateAsync: mockMutate,
      isPending: false,
    }));

    renderComponent();

    const nameInput = await screen.findByDisplayValue('Test Chain');
    fireEvent.change(nameInput, { target: { value: 'Updated Name' } });

    const saveButton = screen.getByText(/save changes/i);
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(mockMutate).toHaveBeenCalledWith(
        expect.objectContaining({
          name: 'Updated Name',
          description: 'Test description',
          color: '#FF6B35',
          nodes: expect.arrayContaining([
            expect.objectContaining({
              entity_type: 'host',
              entity_id: 'host-1',
              sequence_order: 1,
            }),
          ]),
        })
      );
    });
  });

  test('calls onSave callback after successful save', async () => {
    const useAttackChains = require('../../../hooks/useAttackChains');
    const mockMutate = jest.fn().mockResolvedValue(mockChain);
    useAttackChains.useUpdateAttackChain = jest.fn(() => ({
      mutateAsync: mockMutate,
      isPending: false,
    }));

    renderComponent();

    const saveButton = await screen.findByText(/save changes/i);
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(mockProps.onSave).toHaveBeenCalledWith(mockChain);
    });
  });

  test('calls onClose after successful save', async () => {
    const useAttackChains = require('../../../hooks/useAttackChains');
    const mockMutate = jest.fn().mockResolvedValue(mockChain);
    useAttackChains.useUpdateAttackChain = jest.fn(() => ({
      mutateAsync: mockMutate,
      isPending: false,
    }));

    renderComponent();

    const saveButton = await screen.findByText(/save changes/i);
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(mockProps.onClose).toHaveBeenCalled();
    });
  });

  test('shows loading state on save button when saving', async () => {
    const useAttackChains = require('../../../hooks/useAttackChains');
    useAttackChains.useUpdateAttackChain = jest.fn(() => ({
      mutateAsync: jest.fn().mockResolvedValue(mockChain),
      isPending: true,
    }));

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText(/saving/i)).toBeInTheDocument();
    });
  });

  test('calls onClose when cancel button clicked', async () => {
    renderComponent();

    const cancelButton = await screen.findByText(/^cancel$/i);
    fireEvent.click(cancelButton);

    expect(mockProps.onClose).toHaveBeenCalled();
  });

  test('calls onClose when X button clicked', async () => {
    renderComponent();

    const closeButton = screen.getByText('✕');
    fireEvent.click(closeButton);

    expect(mockProps.onClose).toHaveBeenCalled();
  });

  test('does not render when closed', () => {
    renderComponent({ ...mockProps, isOpen: false });
    expect(screen.queryByText(/edit attack chain/i)).not.toBeInTheDocument();
  });
});
