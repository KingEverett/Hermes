import React from 'react';
import { render } from '@testing-library/react';
import { screen, fireEvent, waitFor } from '@testing-library/dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { NotesEditor } from '../NotesEditor';

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

const mockNote = {
  id: 'note_1',
  project_id: 'proj_1',
  entity_type: 'host' as const,
  entity_id: 'host_1',
  content: 'This is a test note with **markdown**',
  author: 'test-user',
  tags: ['important', 'review'],
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-15T00:00:00Z',
};

describe('NotesEditor', () => {
  beforeEach(() => {
    global.fetch = jest.fn();
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.restoreAllMocks();
    jest.useRealTimers();
  });

  test('fetches and displays existing notes', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => [mockNote],
    });

    const queryClient = createTestQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <NotesEditor entityType="host" entityId="host_1" projectId="proj_1" />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/This is a test note/)).toBeInTheDocument();
    });
  });

  test('displays note metadata (author and timestamps)', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => [mockNote],
    });

    const queryClient = createTestQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <NotesEditor entityType="host" entityId="host_1" projectId="proj_1" />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/Author:/)).toBeInTheDocument();
      expect(screen.getByText('test-user')).toBeInTheDocument();
      expect(screen.getByText(/Created:/)).toBeInTheDocument();
      expect(screen.getByText(/Last Updated:/)).toBeInTheDocument();
    });
  });

  test('displays existing tags', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => [mockNote],
    });

    const queryClient = createTestQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <NotesEditor entityType="host" entityId="host_1" projectId="proj_1" />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('important')).toBeInTheDocument();
      expect(screen.getByText('review')).toBeInTheDocument();
    });
  });

  test('allows adding new tags', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => [mockNote],
    });

    const queryClient = createTestQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <NotesEditor entityType="host" entityId="host_1" projectId="proj_1" />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Add a tag...')).toBeInTheDocument();
    });

    const tagInput = screen.getByPlaceholderText('Add a tag...');
    fireEvent.change(tagInput, { target: { value: 'urgent' } });
    fireEvent.click(screen.getByText('Add'));

    expect(screen.getByText('urgent')).toBeInTheDocument();
  });

  test('allows removing tags', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => [mockNote],
    });

    const queryClient = createTestQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <NotesEditor entityType="host" entityId="host_1" projectId="proj_1" />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('important')).toBeInTheDocument();
    });

    // Find and click the remove button for 'important' tag
    const importantTag = screen.getByText('important').closest('span');
    const removeButton = importantTag?.querySelector('button');

    if (removeButton) {
      fireEvent.click(removeButton);
    }

    await waitFor(() => {
      expect(screen.queryByText('important')).not.toBeInTheDocument();
    });
  });

  test('auto-saves note after 2 seconds of inactivity', async () => {
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ ...mockNote, content: 'Updated content' }),
      });

    const queryClient = createTestQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <NotesEditor entityType="host" entityId="host_1" projectId="proj_1" />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Add your notes here/)).toBeInTheDocument();
    });

    const textarea = screen.getByRole('textbox');
    fireEvent.change(textarea, { target: { value: 'New note content' } });

    // Fast-forward time by 2 seconds
    jest.advanceTimersByTime(2000);

    await waitFor(() => {
      expect(screen.getByText(/Saving.../)).toBeInTheDocument();
    });
  });

  test('shows save status indicator', async () => {
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockNote,
      });

    const queryClient = createTestQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <NotesEditor entityType="host" entityId="host_1" projectId="proj_1" />
      </QueryClientProvider>
    );

    await waitFor(() => {
      const textarea = screen.getByRole('textbox');
      fireEvent.change(textarea, { target: { value: 'Test content' } });
    });

    jest.advanceTimersByTime(2000);

    await waitFor(() => {
      expect(screen.getByText(/Saved/)).toBeInTheDocument();
    });
  });

  test('shows empty state when no notes exist', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => [],
    });

    const queryClient = createTestQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <NotesEditor entityType="host" entityId="host_1" projectId="proj_1" />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Add your notes here/)).toBeInTheDocument();
    });
  });
});
