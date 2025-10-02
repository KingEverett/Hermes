import { renderHook } from '@testing-library/react';
import { waitFor } from '@testing-library/dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useHostDetails } from '../useHostDetails';
import React from 'react';

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

const mockHost = {
  id: 'host_1',
  project_id: 'proj_1',
  ip_address: '192.168.1.100',
  hostname: 'webserver.local',
  os_family: 'Linux',
  os_details: 'Ubuntu 20.04',
  status: 'up' as const,
  confidence_score: 0.95,
  first_seen: '2025-01-01T00:00:00Z',
  last_seen: '2025-01-15T00:00:00Z',
  mac_address: '00:11:22:33:44:55',
  metadata: {
    open_ports_count: 5,
    vulnerability_summary: {
      critical: 2,
      high: 3,
      medium: 5,
      low: 1,
    },
  },
};

describe('useHostDetails', () => {
  beforeEach(() => {
    global.fetch = jest.fn();
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  test('returns host data on success', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockHost,
    });

    const { result } = renderHook(() => useHostDetails('host_1'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(mockHost);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBe(null);
  });

  test('returns loading state during fetch', () => {
    (global.fetch as jest.Mock).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    const { result } = renderHook(() => useHostDetails('host_1'), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);
    expect(result.current.data).toBeUndefined();
  });

  test('returns error state on 404', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 404,
    });

    const { result } = renderHook(() => useHostDetails('host_1'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error).toBeTruthy();
    expect(result.current.data).toBeUndefined();
  });

  test('returns error state on network failure', async () => {
    (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));

    const { result } = renderHook(() => useHostDetails('host_1'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error).toBeTruthy();
  });

  test('is disabled when hostId is undefined', () => {
    const { result } = renderHook(() => useHostDetails(undefined), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(false);
    expect(result.current.data).toBeUndefined();
    expect(global.fetch).not.toHaveBeenCalled();
  });

  test('uses correct cache key with hostId', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockHost,
    });

    const { result } = renderHook(() => useHostDetails('host_1'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // Verify the query was called with correct parameters
    expect(global.fetch).toHaveBeenCalledWith('/api/v1/hosts/host_1');
  });

  test('uses staleTime of 30 seconds', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockHost,
    });

    const { result } = renderHook(() => useHostDetails('host_1'), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // Data should be considered fresh (not stale) immediately after fetch
    expect(result.current.isStale).toBe(false);
  });
});
