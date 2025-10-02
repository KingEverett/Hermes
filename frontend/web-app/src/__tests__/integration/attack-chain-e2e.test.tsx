/**
 * Integration tests for Attack Chain workflows (Create + Edit)
 *
 * Tests end-to-end workflows: creation, editing, node management
 */

import React from 'react';
import { render } from '@testing-library/react';
import { screen, fireEvent, waitFor } from '@testing-library/dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import AttackChainCreator from '../../components/visualization/AttackChainCreator';
import AttackChainEditor from '../../components/visualization/AttackChainEditor';
import AttackChainTree from '../../components/layout/AttackChainTree';
import { AttackChain, AttackChainListItem } from '../../types/attackChain';

// Mock hooks
jest.mock('../../hooks/useAttackChains');
jest.mock('../../stores/attackChainVisibilityStore');

const mockChainList: AttackChainListItem[] = [
  {
    id: 'chain-1',
    project_id: 'project-1',
    name: 'Web to DC',
    description: 'Attack path from web server to domain controller',
    color: '#FF6B35',
    node_count: 3,
    created_at: new Date('2025-01-01'),
    updated_at: new Date('2025-01-01'),
  },
];

const mockFullChain: AttackChain = {
  id: 'chain-1',
  project_id: 'project-1',
  name: 'Web to DC',
  description: 'Attack path from web server to domain controller',
  color: '#FF6B35',
  created_at: new Date('2025-01-01'),
  updated_at: new Date('2025-01-01'),
  nodes: [
    {
      id: 'node-1',
      attack_chain_id: 'chain-1',
      entity_type: 'host',
      entity_id: 'host-webserver',
      sequence_order: 1,
      method_notes: 'SQL injection on login form',
      is_branch_point: false,
      created_at: new Date('2025-01-01'),
    },
    {
      id: 'node-2',
      attack_chain_id: 'chain-1',
      entity_type: 'host',
      entity_id: 'host-appserver',
      sequence_order: 2,
      method_notes: 'Lateral movement via SSH key reuse',
      is_branch_point: true,
      branch_description: 'Alternative: pivot through database server',
      created_at: new Date('2025-01-01'),
    },
    {
      id: 'node-3',
      attack_chain_id: 'chain-1',
      entity_type: 'host',
      entity_id: 'host-dc',
      sequence_order: 3,
      method_notes: 'Kerberoasting attack on service account',
      is_branch_point: false,
      created_at: new Date('2025-01-01'),
    },
  ],
};

describe('Attack Chain E2E Workflow', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });
    jest.clearAllMocks();

    // Setup default mocks
    const useAttackChains = require('../../hooks/useAttackChains');
    useAttackChains.useProjectAttackChains = jest.fn(() => ({
      data: mockChainList,
      isLoading: false,
    }));
    useAttackChains.useAttackChain = jest.fn(() => ({
      data: mockFullChain,
      isLoading: false,
      error: null,
    }));
    useAttackChains.useUpdateAttackChain = jest.fn(() => ({
      mutateAsync: jest.fn().mockResolvedValue(mockFullChain),
      isPending: false,
    }));
    useAttackChains.useDeleteAttackChain = jest.fn(() => ({
      mutateAsync: jest.fn().mockResolvedValue({}),
    }));

    const visibilityStore = require('../../stores/attackChainVisibilityStore');
    visibilityStore.useAttackChainVisibilityStore = jest.fn(() => ({
      visibleChainIds: new Set(['chain-1']),
      activeChainId: null,
      toggleChainVisibility: jest.fn(),
      setActiveChain: jest.fn(),
    }));
  });

  const renderInProvider = (component: React.ReactElement) => {
    return render(
      <QueryClientProvider client={queryClient}>
        {component}
      </QueryClientProvider>
    );
  };

  describe('Edit Attack Chain from Tree', () => {
    test('opens editor from context menu', async () => {
      const onEditChain = jest.fn();

      renderInProvider(
        <AttackChainTree
          projectId="project-1"
          onCreateChain={jest.fn()}
          onEditChain={onEditChain}
        />
      );

      // Find chain item
      const chainItem = await screen.findByText('Web to DC');

      // Right-click to open context menu
      fireEvent.contextMenu(chainItem);

      // Click Edit option
      const editButton = await screen.findByText('Edit');
      fireEvent.click(editButton);

      expect(onEditChain).toHaveBeenCalledWith('chain-1');
    });

    test('loads chain data in editor', async () => {
      renderInProvider(
        <AttackChainEditor
          chainId="chain-1"
          projectId="project-1"
          isOpen={true}
          onClose={jest.fn()}
        />
      );

      await waitFor(() => {
        expect(screen.getByDisplayValue('Web to DC')).toBeInTheDocument();
        expect(
          screen.getByDisplayValue('Attack path from web server to domain controller')
        ).toBeInTheDocument();
        expect(screen.getByText('#FF6B35')).toBeInTheDocument();
      });
    });
  });

  describe('Edit Chain Name', () => {
    test('updates chain name and saves', async () => {
      const mockMutate = jest.fn().mockResolvedValue({
        ...mockFullChain,
        name: 'Updated Chain',
      });
      const useAttackChains = require('../../hooks/useAttackChains');
      useAttackChains.useUpdateAttackChain = jest.fn(() => ({
        mutateAsync: mockMutate,
        isPending: false,
      }));

      const onSave = jest.fn();

      renderInProvider(
        <AttackChainEditor
          chainId="chain-1"
          projectId="project-1"
          isOpen={true}
          onClose={jest.fn()}
          onSave={onSave}
        />
      );

      // Change name
      const nameInput = await screen.findByDisplayValue('Web to DC');
      fireEvent.change(nameInput, { target: { value: 'Updated Chain' } });

      // Save
      const saveButton = screen.getByText(/save changes/i);
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(mockMutate).toHaveBeenCalledWith(
          expect.objectContaining({
            name: 'Updated Chain',
          })
        );
      });
    });
  });

  describe('Node Management', () => {
    test('expands node to show details', async () => {
      renderInProvider(
        <AttackChainEditor
          chainId="chain-1"
          projectId="project-1"
          isOpen={true}
          onClose={jest.fn()}
        />
      );

      await waitFor(() => {
        expect(screen.getAllByText('▶')).toHaveLength(3); // 3 nodes
      });

      // Expand first node
      const expandButtons = screen.getAllByText('▶');
      fireEvent.click(expandButtons[0]);

      await waitFor(() => {
        expect(screen.getByDisplayValue('SQL injection on login form')).toBeInTheDocument();
      });
    });

    test('edits method notes for a node', async () => {
      const mockMutate = jest.fn().mockResolvedValue(mockFullChain);
      const useAttackChains = require('../../hooks/useAttackChains');
      useAttackChains.useUpdateAttackChain = jest.fn(() => ({
        mutateAsync: mockMutate,
        isPending: false,
      }));

      renderInProvider(
        <AttackChainEditor
          chainId="chain-1"
          projectId="project-1"
          isOpen={true}
          onClose={jest.fn()}
        />
      );

      // Expand first node
      const expandButtons = await screen.findAllByText('▶');
      fireEvent.click(expandButtons[0]);

      // Update method notes
      const methodInput = await screen.findByDisplayValue('SQL injection on login form');
      fireEvent.change(methodInput, {
        target: { value: 'Updated exploitation method' },
      });

      expect(methodInput).toHaveValue('Updated exploitation method');

      // Save
      const saveButton = screen.getByText(/save changes/i);
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(mockMutate).toHaveBeenCalledWith(
          expect.objectContaining({
            nodes: expect.arrayContaining([
              expect.objectContaining({
                entity_id: 'host-webserver',
                method_notes: 'Updated exploitation method',
              }),
            ]),
          })
        );
      });
    });

    test('toggles branch point status', async () => {
      renderInProvider(
        <AttackChainEditor
          chainId="chain-1"
          projectId="project-1"
          isOpen={true}
          onClose={jest.fn()}
        />
      );

      // Expand first node (not a branch point)
      const expandButtons = await screen.findAllByText('▶');
      fireEvent.click(expandButtons[0]);

      // Toggle branch point
      const checkbox = await screen.findByLabelText(/mark as branch point/i);
      expect(checkbox).not.toBeChecked();

      fireEvent.click(checkbox);
      expect(checkbox).toBeChecked();

      // Branch description field should appear
      await waitFor(() => {
        expect(screen.getByPlaceholderText(/alternative path/i)).toBeInTheDocument();
      });
    });

    test('shows existing branch description when expanded', async () => {
      renderInProvider(
        <AttackChainEditor
          chainId="chain-1"
          projectId="project-1"
          isOpen={true}
          onClose={jest.fn()}
        />
      );

      // Expand second node (has branch point)
      const expandButtons = await screen.findAllByText('▶');
      fireEvent.click(expandButtons[1]);

      await waitFor(() => {
        expect(
          screen.getByDisplayValue('Alternative: pivot through database server')
        ).toBeInTheDocument();
      });
    });

    test('removes node and resequences remaining', async () => {
      const confirmMock = jest.spyOn(window, 'confirm').mockReturnValue(true);

      renderInProvider(
        <AttackChainEditor
          chainId="chain-1"
          projectId="project-1"
          isOpen={true}
          onClose={jest.fn()}
        />
      );

      await waitFor(() => {
        const deleteButtons = screen.getAllByTitle(/remove node/i);
        expect(deleteButtons).toHaveLength(3);
      });

      // Remove first node
      const deleteButtons = screen.getAllByTitle(/remove node/i);
      fireEvent.click(deleteButtons[0]);

      await waitFor(() => {
        // Should now have 2 nodes
        const remainingButtons = screen.getAllByTitle(/remove node/i);
        expect(remainingButtons).toHaveLength(2);
      });

      confirmMock.mockRestore();
    });

    test('prevents removing last node', async () => {
      // Mock chain with only one node
      const useAttackChains = require('../../hooks/useAttackChains');
      useAttackChains.useAttackChain = jest.fn(() => ({
        data: {
          ...mockFullChain,
          nodes: [mockFullChain.nodes[0]],
        },
        isLoading: false,
        error: null,
      }));

      const alertMock = jest.spyOn(window, 'alert').mockImplementation(() => {});

      renderInProvider(
        <AttackChainEditor
          chainId="chain-1"
          projectId="project-1"
          isOpen={true}
          onClose={jest.fn()}
        />
      );

      await waitFor(() => {
        const deleteButtons = screen.getAllByTitle(/remove node/i);
        fireEvent.click(deleteButtons[0]);
      });

      expect(alertMock).toHaveBeenCalledWith(
        expect.stringContaining('Cannot remove the last node')
      );

      alertMock.mockRestore();
    });
  });

  describe('Add Node Workflow', () => {
    test('enters node selection mode', async () => {
      renderInProvider(
        <AttackChainEditor
          chainId="chain-1"
          projectId="project-1"
          isOpen={true}
          onClose={jest.fn()}
        />
      );

      const addButton = await screen.findByText(/\+ add node/i);
      fireEvent.click(addButton);

      await waitFor(() => {
        expect(screen.getByText(/click a node on the graph/i)).toBeInTheDocument();
        expect(screen.getByText(/cancel selection/i)).toBeInTheDocument();
      });
    });

    test('cancels node selection mode', async () => {
      renderInProvider(
        <AttackChainEditor
          chainId="chain-1"
          projectId="project-1"
          isOpen={true}
          onClose={jest.fn()}
        />
      );

      const addButton = await screen.findByText(/\+ add node/i);
      fireEvent.click(addButton);

      const cancelButton = await screen.findByText(/cancel selection/i);
      fireEvent.click(cancelButton);

      await waitFor(() => {
        expect(screen.queryByText(/cancel selection/i)).not.toBeInTheDocument();
      });
    });
  });

  describe('Validation', () => {
    test('prevents save with name too short', async () => {
      renderInProvider(
        <AttackChainEditor
          chainId="chain-1"
          projectId="project-1"
          isOpen={true}
          onClose={jest.fn()}
        />
      );

      const nameInput = await screen.findByDisplayValue('Web to DC');
      fireEvent.change(nameInput, { target: { value: 'AB' } });

      const saveButton = screen.getByText(/save changes/i);
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(screen.getByText(/at least 3 characters/i)).toBeInTheDocument();
      });
    });

    test('prevents save with invalid color', async () => {
      renderInProvider(
        <AttackChainEditor
          chainId="chain-1"
          projectId="project-1"
          isOpen={true}
          onClose={jest.fn()}
        />
      );

      const colorInput = document.querySelector('input[type="color"]') as HTMLInputElement;
      expect(colorInput).toBeTruthy();

      // Manually set invalid value bypassing HTML5 normalization
      Object.defineProperty(colorInput, 'value', {
        writable: true,
        value: 'notacolor',
      });
      fireEvent.change(colorInput, { target: { value: 'notacolor' } });

      const saveButton = screen.getByText(/save changes/i);
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(screen.getByText(/invalid color format/i)).toBeInTheDocument();
      });
    });
  });

  describe('Save and Close Workflow', () => {
    test('calls onSave and onClose after successful save', async () => {
      const mockMutate = jest.fn().mockResolvedValue(mockFullChain);
      const useAttackChains = require('../../hooks/useAttackChains');
      useAttackChains.useUpdateAttackChain = jest.fn(() => ({
        mutateAsync: mockMutate,
        isPending: false,
      }));

      const onSave = jest.fn();
      const onClose = jest.fn();

      renderInProvider(
        <AttackChainEditor
          chainId="chain-1"
          projectId="project-1"
          isOpen={true}
          onClose={onClose}
          onSave={onSave}
        />
      );

      const saveButton = await screen.findByText(/save changes/i);
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(onSave).toHaveBeenCalledWith(mockFullChain);
        expect(onClose).toHaveBeenCalled();
      });
    });

    test('closes without saving when cancel clicked', async () => {
      const onClose = jest.fn();

      renderInProvider(
        <AttackChainEditor
          chainId="chain-1"
          projectId="project-1"
          isOpen={true}
          onClose={onClose}
        />
      );

      const cancelButton = await screen.findByText(/^cancel$/i);
      fireEvent.click(cancelButton);

      expect(onClose).toHaveBeenCalled();
    });
  });

  describe('Error Handling', () => {
    test('displays error when chain fails to load', () => {
      const useAttackChains = require('../../hooks/useAttackChains');
      useAttackChains.useAttackChain = jest.fn(() => ({
        data: null,
        isLoading: false,
        error: new Error('Network error'),
      }));

      renderInProvider(
        <AttackChainEditor
          chainId="chain-1"
          projectId="project-1"
          isOpen={true}
          onClose={jest.fn()}
        />
      );

      expect(screen.getByText(/error loading chain/i)).toBeInTheDocument();
    });

    test('shows alert on save failure', async () => {
      const mockMutate = jest.fn().mockRejectedValue(new Error('Save failed'));
      const useAttackChains = require('../../hooks/useAttackChains');
      useAttackChains.useUpdateAttackChain = jest.fn(() => ({
        mutateAsync: mockMutate,
        isPending: false,
      }));

      const alertMock = jest.spyOn(window, 'alert').mockImplementation(() => {});

      renderInProvider(
        <AttackChainEditor
          chainId="chain-1"
          projectId="project-1"
          isOpen={true}
          onClose={jest.fn()}
        />
      );

      const saveButton = await screen.findByText(/save changes/i);
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(alertMock).toHaveBeenCalledWith(
          expect.stringContaining('Failed to save')
        );
      });

      alertMock.mockRestore();
    });
  });
});
