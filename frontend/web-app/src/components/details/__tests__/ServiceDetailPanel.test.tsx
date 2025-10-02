import React from 'react';
import { render } from '@testing-library/react';
import { screen, waitFor, fireEvent } from '@testing-library/dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ServiceDetailPanel } from '../ServiceDetailPanel';

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

const mockService = {
  id: 'service_1',
  host_id: 'host_1',
  port: 443,
  protocol: 'tcp' as const,
  service_name: 'https',
  product: 'nginx',
  version: '1.18.0',
  banner: 'nginx/1.18.0 (Ubuntu)',
  cpe: 'cpe:/a:nginx:nginx:1.18.0',
  confidence: 'high' as const,
  created_at: '2025-01-15T00:00:00Z',
};

const mockVulnerabilities = [
  {
    id: 'vuln_1',
    cve_id: 'CVE-2021-23017',
    cvss_score: 8.1,
    severity: 'high' as const,
    description: 'DNS resolver off-by-one heap write',
    exploit_available: true,
    cisa_kev: false,
    references: [],
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
  },
];

describe('ServiceDetailPanel', () => {
  beforeEach(() => {
    global.fetch = jest.fn();
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  test('renders service details with complete data', async () => {
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockService,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockVulnerabilities,
      });

    const queryClient = createTestQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <ServiceDetailPanel serviceId="service_1" />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('443')).toBeInTheDocument();
    });

    expect(screen.getByText('TCP')).toBeInTheDocument();
    expect(screen.getByText('https')).toBeInTheDocument();
    expect(screen.getByText('nginx')).toBeInTheDocument();
    expect(screen.getByText('1.18.0')).toBeInTheDocument();
  });

  test('displays confidence level indicator', async () => {
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockService,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      });

    const queryClient = createTestQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <ServiceDetailPanel serviceId="service_1" />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('HIGH')).toBeInTheDocument();
    });
  });

  test('shows banner in expandable code block', async () => {
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockService,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      });

    const queryClient = createTestQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <ServiceDetailPanel serviceId="service_1" />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Show Banner')).toBeInTheDocument();
    });

    // Banner should not be visible initially
    expect(screen.queryByText('nginx/1.18.0 (Ubuntu)')).not.toBeInTheDocument();

    // Click to expand
    fireEvent.click(screen.getByText('Show Banner'));

    // Banner should now be visible
    await waitFor(() => {
      expect(screen.getByText('nginx/1.18.0 (Ubuntu)')).toBeInTheDocument();
    });
  });

  test('displays related vulnerabilities with severity badges', async () => {
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockService,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => mockVulnerabilities,
      });

    const queryClient = createTestQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <ServiceDetailPanel serviceId="service_1" />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('CVE-2021-23017')).toBeInTheDocument();
      expect(screen.getByText('HIGH')).toBeInTheDocument();
      expect(screen.getByText('8.1')).toBeInTheDocument();
    });
  });

  test('handles missing product and version gracefully', async () => {
    const serviceWithoutProduct = {
      ...mockService,
      product: undefined,
      version: undefined,
    };

    (global.fetch as jest.Mock)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => serviceWithoutProduct,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      });

    const queryClient = createTestQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <ServiceDetailPanel serviceId="service_1" />
      </QueryClientProvider>
    );

    // Product/Version section should not be rendered if both are missing
    await waitFor(() => {
      expect(screen.getByText('https')).toBeInTheDocument();
    });

    expect(screen.queryByText('Product / Version')).not.toBeInTheDocument();
  });

  test('shows error state on fetch failure', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      status: 404,
    });

    const queryClient = createTestQueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <ServiceDetailPanel serviceId="service_1" />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('Unable to load service details')).toBeInTheDocument();
    });
  });
});
