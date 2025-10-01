/**
 * Smoke tests for AttackChainCreator component
 *
 * DEV TEAM: Verify modal rendering and basic form interactions.
 * Goal: Ensure creator modal opens, accepts input, and submits.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import AttackChainCreator from '../AttackChainCreator';

// Mock the create hook
jest.mock('../../../hooks/useAttackChains');

const mockProps = {
  projectId: 'project-1',
  isOpen: true,
  onClose: jest.fn(),
  onNodeSelect: jest.fn(),
};

describe('AttackChainCreator', () => {
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
    useAttackChains.useCreateAttackChain = jest.fn(() => ({
      mutateAsync: jest.fn().mockResolvedValue({ id: 'new-chain-id' }),
      isLoading: false,
    }));
  });

  const renderComponent = (props = mockProps) => {
    return render(
      <QueryClientProvider client={queryClient}>
        <AttackChainCreator {...props} />
      </QueryClientProvider>
    );
  };

  test('renders without crashing when open', () => {
    renderComponent();
    // Modal should be visible
    expect(screen.getByRole('dialog') || screen.getByText(/create attack chain/i)).toBeTruthy();
  });

  test('does not render when closed', () => {
    renderComponent({ ...mockProps, isOpen: false });
    // Modal should not be in the document
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  test('displays name input field', () => {
    renderComponent();
    const nameInput = screen.getByLabelText(/name/i) || screen.getByPlaceholderText(/chain name/i);
    expect(nameInput).toBeInTheDocument();
  });

  test('displays description textarea', () => {
    renderComponent();
    const descInput = screen.getByLabelText(/description/i) || screen.getByPlaceholderText(/description/i);
    expect(descInput).toBeInTheDocument();
  });

  test('displays color picker', () => {
    renderComponent();
    const colorInput = screen.getByLabelText(/color/i) || screen.getByDisplayValue('#FF6B35');
    expect(colorInput).toBeInTheDocument();
  });

  test('accepts text input for chain name', () => {
    renderComponent();
    const nameInput = screen.getByLabelText(/name/i) || screen.getByPlaceholderText(/chain name/i);

    fireEvent.change(nameInput, { target: { value: 'Test Attack Chain' } });
    expect(nameInput).toHaveValue('Test Attack Chain');
  });

  test('accepts text input for description', () => {
    renderComponent();
    const descInput = screen.getByLabelText(/description/i) || screen.getByPlaceholderText(/description/i);

    fireEvent.change(descInput, { target: { value: 'Test description' } });
    expect(descInput).toHaveValue('Test description');
  });

  test('shows cancel button', () => {
    renderComponent();
    const cancelButton = screen.getByText(/cancel/i);
    expect(cancelButton).toBeInTheDocument();
  });

  test('calls onClose when cancel button clicked', () => {
    renderComponent();
    const cancelButton = screen.getByText(/cancel/i);

    fireEvent.click(cancelButton);
    expect(mockProps.onClose).toHaveBeenCalledTimes(1);
  });

  test('shows create/save button', () => {
    renderComponent();
    const saveButton = screen.getByText(/create|save/i);
    expect(saveButton).toBeInTheDocument();
  });

  test('displays step indicator or progress', () => {
    const { container } = renderComponent();
    // Look for step indicators (1, 2, 3) or "Step 1 of 3" text
    const hasSteps =
      screen.queryByText(/step/i) ||
      container.querySelector('[class*="step"]') ||
      screen.queryByText(/1.*2.*3/);

    expect(hasSteps).toBeTruthy();
  });

  test('prevents submission with empty name', async () => {
    renderComponent();

    // Try to submit with empty name
    const saveButton = screen.getByText(/create|save/i);
    fireEvent.click(saveButton);

    // Should show validation error or not call mutateAsync
    const useAttackChains = require('../../../hooks/useAttackChains');
    const mockMutate = useAttackChains.useCreateAttackChain().mutateAsync;

    await waitFor(() => {
      // Either mutation wasn't called, or an error message is shown
      expect(mockMutate).not.toHaveBeenCalled();
    });
  });

  test('handles form submission with valid data', async () => {
    renderComponent();

    const nameInput = screen.getByLabelText(/name/i) || screen.getByPlaceholderText(/chain name/i);
    fireEvent.change(nameInput, { target: { value: 'Valid Chain Name' } });

    const saveButton = screen.getByText(/create|save/i);
    fireEvent.click(saveButton);

    const useAttackChains = require('../../../hooks/useAttackChains');
    const mockMutate = useAttackChains.useCreateAttackChain().mutateAsync;

    await waitFor(() => {
      expect(mockMutate).toHaveBeenCalled();
    });
  });
});
