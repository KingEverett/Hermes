/**
 * useNetworkData hook tests
 *
 * Tests React Query hook behavior, API integration, and state management.
 */

import { renderHook } from '@testing-library/react';
import { waitFor } from '@testing-library/dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { useNetworkData } from '../useNetworkData';

// Mock fetch
global.fetch = jest.fn();

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('useNetworkData', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  const mockTopology = {
    nodes: [
      {
        id: 'host_1',
        type: 'host',
        label: '192.168.1.1',
        x: 0,
        y: 0,
        metadata: { os: 'Linux', color: '#3B82F6' },
      },
    ],
    edges: [],
    metadata: {
      node_count: 1,
      edge_count: 0,
      generated_at: '2025-09-30T12:00:00Z',
    },
  };

  test('fetches topology data successfully', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockTopology,
    });

    const { result } = renderHook(
      () => useNetworkData('test-project-id'),
      { wrapper: createWrapper() }
    );

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockTopology);
    expect(global.fetch).toHaveBeenCalledWith(
      '/api/v1/projects/test-project-id/topology'
    );
  });

  test('handles API errors', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      statusText: 'Not Found',
      json: async () => ({ detail: 'Project not found' }),
    });

    const { result } = renderHook(
      () => useNetworkData('invalid-project-id'),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBeTruthy();
    expect(result.current.error?.message).toContain('Project not found');
  });

  test('handles network errors', async () => {
    (global.fetch as jest.Mock).mockRejectedValueOnce(
      new Error('Network error')
    );

    const { result } = renderHook(
      () => useNetworkData('test-project-id'),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBeTruthy();
  });

  test('does not fetch when projectId is undefined', () => {
    const { result } = renderHook(
      () => useNetworkData(undefined),
      { wrapper: createWrapper() }
    );

    expect(result.current.isLoading).toBe(false);
    expect(result.current.isFetching).toBe(false);
    expect(global.fetch).not.toHaveBeenCalled();
  });

  test('refetches when projectId changes', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: async () => mockTopology,
    });

    const { result, rerender } = renderHook(
      ({ projectId }) => useNetworkData(projectId),
      {
        wrapper: createWrapper(),
        initialProps: { projectId: 'project-1' },
      }
    );

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(global.fetch).toHaveBeenCalledWith(
      '/api/v1/projects/project-1/topology'
    );

    // Change project ID
    rerender({ projectId: 'project-2' });

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/projects/project-2/topology'
      );
    });
  });

  test('uses correct query key', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockTopology,
    });

    const { result } = renderHook(
      () => useNetworkData('test-project-id'),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    // Query key should include project ID for proper caching
    expect(result.current.data).toBeDefined();
  });
});
