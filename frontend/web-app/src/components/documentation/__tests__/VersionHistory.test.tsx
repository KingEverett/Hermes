import React from 'react';
import { render } from '@testing-library/react';
import { screen, waitFor } from '@testing-library/dom';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { VersionHistory } from '../VersionHistory';
import * as useDocumentationHook from '../../../hooks/useDocumentation';

jest.mock('../../../hooks/useDocumentation');

const mockUseDocumentation = useDocumentationHook as jest.Mocked<typeof useDocumentationHook>;

describe('VersionHistory', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });

    mockUseDocumentation.useVersionHistory.mockReturnValue({
      data: [
        {
          id: 'v1',
          documentation_id: 'doc-1',
          content: '# Version 1 Content',
          version: 1,
          created_at: '2025-09-30T10:00:00Z',
          author: 'user1@example.com',
        },
        {
          id: 'v2',
          documentation_id: 'doc-1',
          content: '# Version 2 Content',
          version: 2,
          created_at: '2025-09-30T11:00:00Z',
          author: 'user2@example.com',
        },
      ],
      isLoading: false,
      error: null,
    } as any);

    mockUseDocumentation.useRollback.mockReturnValue({
      mutate: jest.fn(),
      isPending: false,
      isError: false,
      error: null,
    } as any);
  });

  const renderWithQueryClient = (component: React.ReactElement) => {
    return render(
      <QueryClientProvider client={queryClient}>
        {component}
      </QueryClientProvider>
    );
  };

  it('renders version history list', () => {
    renderWithQueryClient(<VersionHistory documentationId="doc-1" />);

    expect(screen.getByText(/Version 1/i)).toBeInTheDocument();
    expect(screen.getByText(/Version 2/i)).toBeInTheDocument();
    expect(screen.getByText(/user1@example.com/i)).toBeInTheDocument();
    expect(screen.getByText(/user2@example.com/i)).toBeInTheDocument();
  });

  it('marks current version', () => {
    renderWithQueryClient(<VersionHistory documentationId="doc-1" />);

    expect(screen.getByText(/Current/i)).toBeInTheDocument();
  });

  it('shows loading state', () => {
    mockUseDocumentation.useVersionHistory.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    } as any);

    renderWithQueryClient(<VersionHistory documentationId="doc-1" />);

    expect(screen.getByText(/Loading version history/i)).toBeInTheDocument();
  });

  it('shows error state', () => {
    mockUseDocumentation.useVersionHistory.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error('Failed to load versions'),
    } as any);

    renderWithQueryClient(<VersionHistory documentationId="doc-1" />);

    expect(screen.getByText(/Error loading version history/i)).toBeInTheDocument();
  });

  it('shows no history message when empty', () => {
    mockUseDocumentation.useVersionHistory.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    } as any);

    renderWithQueryClient(<VersionHistory documentationId="doc-1" />);

    expect(screen.getByText(/No version history available/i)).toBeInTheDocument();
  });

  it('handles rollback with confirmation', async () => {
    const user = userEvent.setup();
    global.confirm = jest.fn(() => true);
    const mockMutate = jest.fn();

    mockUseDocumentation.useRollback.mockReturnValue({
      mutate: mockMutate,
      isPending: false,
      isError: false,
      error: null,
    } as any);

    renderWithQueryClient(<VersionHistory documentationId="doc-1" />);

    const rollbackButtons = screen.getAllByRole('button', { name: /Rollback/i });
    await user.click(rollbackButtons[0]);

    expect(global.confirm).toHaveBeenCalled();
    expect(mockMutate).toHaveBeenCalledWith('v2');
  });

  it('cancels rollback when not confirmed', async () => {
    const user = userEvent.setup();
    global.confirm = jest.fn(() => false);
    const mockMutate = jest.fn();

    mockUseDocumentation.useRollback.mockReturnValue({
      mutate: mockMutate,
      isPending: false,
      isError: false,
      error: null,
    } as any);

    renderWithQueryClient(<VersionHistory documentationId="doc-1" />);

    const rollbackButtons = screen.getAllByRole('button', { name: /Rollback/i });
    await user.click(rollbackButtons[0]);

    expect(global.confirm).toHaveBeenCalled();
    expect(mockMutate).not.toHaveBeenCalled();
  });

  it('opens preview modal when preview button clicked', async () => {
    const user = userEvent.setup();

    renderWithQueryClient(<VersionHistory documentationId="doc-1" />);

    const previewButtons = screen.getAllByRole('button', { name: /👁️/i });
    await user.click(previewButtons[0]);

    await waitFor(() => {
      expect(screen.getByText(/Version 1 Preview/i)).toBeInTheDocument();
    });
  });

  it('closes preview modal', async () => {
    const user = userEvent.setup();

    renderWithQueryClient(<VersionHistory documentationId="doc-1" />);

    // Open preview
    const previewButtons = screen.getAllByRole('button', { name: /👁️/i });
    await user.click(previewButtons[0]);

    // Close preview
    const closeButton = screen.getByRole('button', { name: /Close/i });
    await user.click(closeButton);

    await waitFor(() => {
      expect(screen.queryByText(/Version 1 Preview/i)).not.toBeInTheDocument();
    });
  });

  it('shows rollback in progress state', () => {
    mockUseDocumentation.useRollback.mockReturnValue({
      mutate: jest.fn(),
      isPending: true,
      isError: false,
      error: null,
    } as any);

    renderWithQueryClient(<VersionHistory documentationId="doc-1" />);

    expect(screen.getByText(/Rolling back to selected version/i)).toBeInTheDocument();
  });

  it('shows rollback error state', () => {
    mockUseDocumentation.useRollback.mockReturnValue({
      mutate: jest.fn(),
      isPending: false,
      isError: true,
      error: new Error('Rollback failed'),
    } as any);

    renderWithQueryClient(<VersionHistory documentationId="doc-1" />);

    expect(screen.getByText(/Error rolling back/i)).toBeInTheDocument();
  });
});
