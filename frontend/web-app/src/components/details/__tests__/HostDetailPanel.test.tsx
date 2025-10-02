import React from 'react';
import { render } from '@testing-library/react';
import { screen, waitFor } from '@testing-library/dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { HostDetailPanel } from '../HostDetailPanel';

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

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

describe('HostDetailPanel', () => {
  beforeEach(() => {
    global.fetch = jest.fn();
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  test('renders host details with complete data', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockHost,
    });

    const queryClient = createTestQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <HostDetailPanel hostId="host_1" />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('192.168.1.100')).toBeInTheDocument();
    });

    expect(screen.getByText('webserver.local')).toBeInTheDocument();
    expect(screen.getByText('Linux')).toBeInTheDocument();
    expect(screen.getByText('Ubuntu 20.04')).toBeInTheDocument();
    expect(screen.getByText('UP')).toBeInTheDocument();
    expect(screen.getByText('00:11:22:33:44:55')).toBeInTheDocument();
  });

  test('shows "N/A" for missing hostname', async () => {
    const hostWithoutHostname = {
      ...mockHost,
      hostname: undefined,
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => hostWithoutHostname,
    });

    const queryClient = createTestQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <HostDetailPanel hostId="host_1" />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('N/A')).toBeInTheDocument();
    });
  });

  test('shows "OS not detected" for missing OS details', async () => {
    const hostWithoutOS = {
      ...mockHost,
      os_family: undefined,
      os_details: undefined,
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => hostWithoutOS,
    });

    const queryClient = createTestQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <HostDetailPanel hostId="host_1" />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('OS not detected')).toBeInTheDocument();
    });
  });

  test('displays status badge with correct styling', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockHost,
    });

    const queryClient = createTestQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <HostDetailPanel hostId="host_1" />
      </QueryClientProvider>
    );

    await waitFor(() => {
      const statusBadge = screen.getByText('UP');
      expect(statusBadge).toHaveClass('bg-green-600');
    });
  });

  test('displays vulnerability summary with severity counts', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => mockHost,
    });

    const queryClient = createTestQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <HostDetailPanel hostId="host_1" />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Critical')).toBeInTheDocument();
      expect(screen.getByText('2')).toBeInTheDocument();
      expect(screen.getByText('High')).toBeInTheDocument();
      expect(screen.getByText('3')).toBeInTheDocument();
    });
  });

  test('shows loading state', () => {
    (global.fetch as jest.Mock).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    const queryClient = createTestQueryClient();

    const { container } = render(
      <QueryClientProvider client={queryClient}>
        <HostDetailPanel hostId="host_1" />
      </QueryClientProvider>
    );

    // Check for loading skeleton by class name
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument();
  });

  test('shows error state on fetch failure', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 500,
    });

    const queryClient = createTestQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <HostDetailPanel hostId="host_1" />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Unable to load host details')).toBeInTheDocument();
    });
  });
});
