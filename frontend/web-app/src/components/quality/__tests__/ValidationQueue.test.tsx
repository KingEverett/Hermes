import React from 'react';
import { render } from '@testing-library/react';
import { screen, fireEvent } from '@testing-library/dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ValidationQueue from '../ValidationQueue';
import * as hooks from '../../../hooks/useQualityMetrics';

// Mock the hooks
jest.mock('../../../hooks/useQualityMetrics');

// Mock the quality store
jest.mock('../../../stores/qualityStore', () => ({
  useQualityStore: () => ({
    filters: { priority: null, status: null, finding_type: null },
    setFilters: jest.fn(),
    setSelectedFinding: jest.fn(),
    setShowValidationModal: jest.fn(),
  }),
}));

const mockUseValidationQueue = hooks.useValidationQueue as jest.MockedFunction<
  typeof hooks.useValidationQueue
>;

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

describe('ValidationQueue', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('displays loading state', () => {
    mockUseValidationQueue.mockReturnValue({
      data: undefined,
      isLoading: true,
    } as any);

    render(<ValidationQueue />, { wrapper: createWrapper() });

    expect(screen.getByText('Loading queue items...')).toBeInTheDocument();
  });

  it('displays empty state when no items', () => {
    mockUseValidationQueue.mockReturnValue({
      data: { items: [], total: 0 },
      isLoading: false,
    } as any);

    render(<ValidationQueue />, { wrapper: createWrapper() });

    expect(screen.getByText('No items in validation queue')).toBeInTheDocument();
  });

  it('renders queue items correctly', () => {
    mockUseValidationQueue.mockReturnValue({
      data: {
        items: [
          {
            id: '1',
            finding_type: 'service_vulnerability',
            finding_id: 'abc123def456',
            priority: 'high',
            status: 'pending',
            assigned_to: null,
            created_at: '2025-01-01T00:00:00Z',
            reviewed_at: null,
            review_notes: null,
          },
        ],
        total: 1,
      },
      isLoading: false,
    } as any);

    render(<ValidationQueue />, { wrapper: createWrapper() });

    expect(screen.getByText('HIGH')).toBeInTheDocument();
    expect(screen.getByText('service_vulnerability')).toBeInTheDocument();
    expect(screen.getByText(/Finding ID: abc123de/)).toBeInTheDocument();
  });

  it('renders priority badge with correct color', () => {
    mockUseValidationQueue.mockReturnValue({
      data: {
        items: [
          {
            id: '1',
            finding_type: 'service_vulnerability',
            finding_id: 'abc123',
            priority: 'critical',
            status: 'pending',
            assigned_to: null,
            created_at: '2025-01-01T00:00:00Z',
            reviewed_at: null,
            review_notes: null,
          },
        ],
        total: 1,
      },
      isLoading: false,
    } as any);

    const { container } = render(<ValidationQueue />, { wrapper: createWrapper() });

    const badge = container.querySelector('.bg-red-100');
    expect(badge).toBeInTheDocument();
    expect(badge?.textContent).toBe('CRITICAL');
  });

  it('displays total count', () => {
    mockUseValidationQueue.mockReturnValue({
      data: {
        items: [],
        total: 42,
      },
      isLoading: false,
    } as any);

    render(<ValidationQueue />, { wrapper: createWrapper() });

    expect(screen.getByText('42 items')).toBeInTheDocument();
  });
});
