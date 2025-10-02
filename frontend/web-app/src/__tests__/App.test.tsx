/**
 * App integration tests
 *
 * Tests for the main App component including loading states, error handling,
 * and integration with ProjectView.
 *
 * Test Infrastructure:
 * - MSW (Mock Service Worker) v1 for API mocking (configured in setupTests.ts)
 * - renderWithQueryClient for isolated React Query cache per test
 * - Each test gets a fresh QueryClient to prevent cache pollution
 *
 * Test Isolation Pattern:
 * The renderApp() helper wraps AppContent with:
 * 1. Fresh QueryClient (via renderWithQueryClient) - prevents cache pollution
 * 2. ErrorBoundary - catches React errors
 *
 * Why AppContent instead of App?
 * App.tsx creates its own singleton QueryClient. To ensure test isolation,
 * we render AppContent directly and provide our own isolated QueryClient
 * through renderWithQueryClient.
 *
 * Usage in other test files:
 * ```typescript
 * import { renderWithQueryClient } from '../test-utils/query-test-wrapper';
 * renderWithQueryClient(<YourComponent />);
 * ```
 */

import { screen, waitFor } from '@testing-library/dom';
import userEvent from '@testing-library/user-event';
import { server, rest } from '../test-utils/msw-server';
import { renderWithQueryClient } from '../test-utils/query-test-wrapper';
import { AppContent } from '../App';
import { ErrorBoundary } from '../components/common/ErrorBoundary';

// Mock ProjectView component
jest.mock('../pages/ProjectView', () => ({
  ProjectView: ({ projectId }: { projectId: string}) => (
    <div data-testid="project-view">ProjectView: {projectId}</div>
  ),
}));

// Helper to render AppContent with isolated QueryClient and ErrorBoundary
function renderApp() {
  return renderWithQueryClient(
    <ErrorBoundary>
      <AppContent />
    </ErrorBoundary>
  );
}

describe('App', () => {
  it('renders loading state initially', () => {
    // Override with a handler that delays indefinitely
    server.use(
      rest.get('/api/v1/projects/', (req, res, ctx) => {
        return res(ctx.delay('infinite'));
      })
    );

    renderApp();

    expect(screen.getByText('Loading Hermes...')).toBeInTheDocument();
  });

  it('renders ProjectView when project loads successfully', async () => {
    const mockProjects = [
      {
        id: 'test-project-id-123',
        name: 'Test Project',
        description: 'A test project',
        created_at: '2025-10-01T00:00:00Z',
      },
    ];

    server.use(
      rest.get('/api/v1/projects/', (req, res, ctx) => {
        return res(ctx.json(mockProjects));
      })
    );

    renderApp();

    // Wait for ProjectView to appear
    await waitFor(
      () => {
        expect(screen.getByTestId('project-view')).toBeInTheDocument();
      },
      { timeout: 3000 }
    );

    expect(screen.getByText('ProjectView: test-project-id-123')).toBeInTheDocument();
  });

  it('shows error UI when API fails', async () => {
    server.use(
      rest.get('/api/v1/projects/', (req, res, ctx) => {
        return res(ctx.status(500), ctx.json({ error: 'Network error' }));
      })
    );

    renderApp();

    await waitFor(
      () => {
        expect(screen.getByText('Cannot connect to backend')).toBeInTheDocument();
      },
      { timeout: 3000 }
    );

    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
  });

  it('shows error UI when fetch returns non-ok response', async () => {
    server.use(
      rest.get('/api/v1/projects/', (req, res, ctx) => {
        return res(ctx.status(500, 'Internal Server Error'));
      })
    );

    renderApp();

    await waitFor(
      () => {
        expect(screen.getByText('Cannot connect to backend')).toBeInTheDocument();
      },
      { timeout: 3000 }
    );

    expect(
      screen.getByText(/Failed to fetch projects/i)
    ).toBeInTheDocument();
  });

  it('shows empty state when no projects exist', async () => {
    server.use(
      rest.get('/api/v1/projects/', (req, res, ctx) => {
        return res(ctx.json([])); // Empty array
      })
    );

    renderApp();

    await waitFor(
      () => {
        expect(screen.getByText('No projects found')).toBeInTheDocument();
      },
      { timeout: 3000 }
    );

    expect(
      screen.getByText('Import your first scan to get started.')
    ).toBeInTheDocument();
  });

  it('retry button refetches data on error', async () => {
    const user = userEvent.setup();

    // First call fails
    server.use(
      rest.get('/api/v1/projects/', (req, res, ctx) => {
        return res.once(ctx.status(500));
      })
    );

    renderApp();

    // Wait for error to appear
    await waitFor(
      () => {
        expect(screen.getByText('Cannot connect to backend')).toBeInTheDocument();
      },
      { timeout: 3000 }
    );

    // Mock successful retry
    const mockProjects = [
      {
        id: 'retry-project-id',
        name: 'Retry Project',
        created_at: '2025-10-01T00:00:00Z',
      },
    ];

    server.use(
      rest.get('/api/v1/projects/', (req, res, ctx) => {
        return res(ctx.json(mockProjects));
      })
    );

    // Click retry button
    const retryButton = screen.getByRole('button', { name: /retry/i });
    await user.click(retryButton);

    // Should now show ProjectView
    await waitFor(
      () => {
        expect(screen.getByTestId('project-view')).toBeInTheDocument();
      },
      { timeout: 3000 }
    );

    expect(screen.getByText('ProjectView: retry-project-id')).toBeInTheDocument();
  });

  it('QueryClientProvider is properly configured', async () => {
    const mockProjects = [
      {
        id: 'config-test-id',
        name: 'Config Test',
        created_at: '2025-10-01T00:00:00Z',
      },
    ];

    server.use(
      rest.get('/api/v1/projects/', (req, res, ctx) => {
        return res(ctx.json(mockProjects));
      })
    );

    renderApp();

    // Verify QueryClient is working by checking if ProjectView renders
    await waitFor(
      () => {
        expect(screen.getByTestId('project-view')).toBeInTheDocument();
      },
      { timeout: 3000 }
    );
  });

  it('applies dark theme styling to root element', () => {
    // Override with a handler that delays indefinitely
    server.use(
      rest.get('/api/v1/projects/', (req, res, ctx) => {
        return res(ctx.delay('infinite'));
      })
    );

    const { container } = renderApp();

    // Check loading state has dark theme
    const loadingDiv = container.querySelector('.min-h-screen.bg-gray-900');
    expect(loadingDiv).toBeInTheDocument();
  });

  it('renders first project as default when multiple projects exist', async () => {
    const mockProjects = [
      {
        id: 'first-project',
        name: 'First Project',
        created_at: '2025-10-01T00:00:00Z',
      },
      {
        id: 'second-project',
        name: 'Second Project',
        created_at: '2025-10-01T01:00:00Z',
      },
    ];

    server.use(
      rest.get('/api/v1/projects/', (req, res, ctx) => {
        return res(ctx.json(mockProjects));
      })
    );

    renderApp();

    await waitFor(
      () => {
        expect(screen.getByText('ProjectView: first-project')).toBeInTheDocument();
      },
      { timeout: 3000 }
    );
  });
});
