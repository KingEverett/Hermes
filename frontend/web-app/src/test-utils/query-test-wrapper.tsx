/**
 * React Query test wrapper for isolated QueryClient per test
 *
 * This wrapper ensures each test gets a fresh QueryClient instance,
 * preventing cache pollution between tests. The QueryClient is configured
 * with test-appropriate settings:
 * - retry: false (no automatic retries in tests)
 * - gcTime: 0 (no garbage collection delay)
 * - staleTime: 0 (data immediately stale, always refetch)
 *
 * Usage:
 *   import { renderWithQueryClient } from '../test-utils/query-test-wrapper';
 *   renderWithQueryClient(<App />);
 *
 * @see https://tanstack.com/query/latest/docs/react/guides/testing
 */

import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, RenderOptions, RenderResult } from '@testing-library/react';

/**
 * Creates a new QueryClient instance configured for testing
 *
 * Test configuration differs from production:
 * - No retries (fail fast in tests)
 * - No cache persistence (gcTime: 0)
 * - No stale time (always fetch fresh data)
 */
export function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,      // Don't retry failed queries in tests
        gcTime: 0,         // Don't keep unused data in cache
        staleTime: 0,      // Data is immediately stale
      },
      mutations: {
        retry: false,      // Don't retry failed mutations in tests
      },
    },
  });
}

/**
 * Renders a component wrapped in a fresh QueryClientProvider for testing
 *
 * Each call creates a new QueryClient instance, ensuring test isolation.
 * MSW handlers (if configured) will work normally with this wrapper.
 *
 * @param ui - React element to render
 * @param options - Additional render options from @testing-library/react
 * @returns RenderResult from @testing-library/react
 *
 * @example
 * ```tsx
 * renderWithQueryClient(<App />);
 * await waitFor(() => expect(screen.getByText('Success')).toBeInTheDocument());
 * ```
 */
export function renderWithQueryClient(
  ui: React.ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
): RenderResult {
  const testQueryClient = createTestQueryClient();

  return render(
    <QueryClientProvider client={testQueryClient}>
      {ui}
    </QueryClientProvider>,
    options
  );
}
