import React from 'react';
import { render } from '@testing-library/react';
import { screen, fireEvent, waitFor } from '@testing-library/dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { DetailTabs } from '../DetailTabs';

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

describe('DetailTabs', () => {
  beforeEach(() => {
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: async () => [],
      })
    ) as jest.Mock;
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  test('renders all three tabs', () => {
    const queryClient = createTestQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <DetailTabs nodeType="host" nodeId="host_1" projectId="proj_1" />
      </QueryClientProvider>
    );

    expect(screen.getByText('Technical Details')).toBeInTheDocument();
    expect(screen.getByText('Vulnerabilities & Research')).toBeInTheDocument();
    expect(screen.getByText('Notes')).toBeInTheDocument();
  });

  test('switches tabs on click', () => {
    const queryClient = createTestQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <DetailTabs nodeType="host" nodeId="host_1" projectId="proj_1" />
      </QueryClientProvider>
    );

    const detailsTab = screen.getByText('Technical Details');
    const vulnTab = screen.getByText('Vulnerabilities & Research');
    const notesTab = screen.getByText('Notes');

    // Initially on Details tab
    expect(detailsTab).toHaveClass('border-blue-600');
    expect(vulnTab).not.toHaveClass('border-blue-600');

    // Click Vulnerabilities tab
    fireEvent.click(vulnTab);
    expect(vulnTab).toHaveClass('border-blue-600');
    expect(detailsTab).not.toHaveClass('border-blue-600');

    // Click Notes tab
    fireEvent.click(notesTab);
    expect(notesTab).toHaveClass('border-blue-600');
    expect(vulnTab).not.toHaveClass('border-blue-600');
  });

  test('active tab has blue border and correct text color', () => {
    const queryClient = createTestQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <DetailTabs nodeType="host" nodeId="host_1" projectId="proj_1" />
      </QueryClientProvider>
    );

    const detailsTab = screen.getByText('Technical Details');
    const vulnTab = screen.getByText('Vulnerabilities & Research');

    // Active tab (Details) should have blue border and gray-100 text
    expect(detailsTab).toHaveClass('text-gray-100');
    expect(detailsTab).toHaveClass('border-blue-600');

    // Inactive tab should have gray-400 text
    expect(vulnTab).toHaveClass('text-gray-400');
    expect(vulnTab).not.toHaveClass('border-blue-600');
  });

  test('renders HostDetailPanel for host type', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        id: 'host_1',
        ip_address: '192.168.1.1',
        status: 'up',
        first_seen: '2025-01-01T00:00:00Z',
        last_seen: '2025-01-15T00:00:00Z',
        metadata: {},
      }),
    });

    const queryClient = createTestQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <DetailTabs nodeType="host" nodeId="host_1" projectId="proj_1" />
      </QueryClientProvider>
    );

    // Should render HostDetailPanel content
    await waitFor(() => {
      expect(screen.getByText('192.168.1.1')).toBeInTheDocument();
    });
  });

  test('renders ServiceDetailPanel for service type', async () => {
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          id: 'service_1',
          host_id: 'host_1',
          port: 80,
          protocol: 'tcp',
          confidence: 'high',
          created_at: '2025-01-01T00:00:00Z',
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      });

    const queryClient = createTestQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <DetailTabs nodeType="service" nodeId="service_1" projectId="proj_1" />
      </QueryClientProvider>
    );

    // Should render ServiceDetailPanel content
    await waitFor(() => {
      expect(screen.getByText('80')).toBeInTheDocument();
    });
  });

  test('vulnerabilities tab shows research status and vulnerability list', () => {
    const queryClient = createTestQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <DetailTabs nodeType="service" nodeId="service_1" projectId="proj_1" />
      </QueryClientProvider>
    );

    // Switch to vulnerabilities tab
    fireEvent.click(screen.getByText('Vulnerabilities & Research'));

    expect(screen.getByText('Research Status')).toBeInTheDocument();
    expect(screen.getByText('Identified Vulnerabilities')).toBeInTheDocument();
  });
});
