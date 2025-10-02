# Testing Strategy

**Last Updated:** 2025-10-02

## Introduction

This document outlines the testing strategy for the Hermes project, documenting actual testing patterns used in Stories 3.1-3.10. Our testing approach emphasizes integration testing with Mock Service Worker (MSW), isolated React Query test environments, and comprehensive component testing.

## Testing Philosophy

### Testing Pyramid Approach

```
        /\
       /  \        E2E Tests (Cypress)
      /----\
     /      \      Integration Tests (MSW-based)
    /--------\
   /          \    Unit Tests (Components, Hooks, Stores)
  /____________\
```

**Current Coverage: All Test Levels**
- **E2E Tests:** Cypress tests for critical user workflows with real API (Story 3.12)
- **Integration Tests:** MSW-based tests for component integration and API mocking
- **Unit Tests:** Component tests, hooks, and utility functions

**Why Multiple Test Levels?**
- **E2E Tests:** Verify full application stack with real backend interactions
- **Integration Tests:** Fast, reliable tests with mocked APIs for component integration
- **Unit Tests:** Focused tests for individual components and utilities
- Each level catches different types of bugs and provides different value

### Test Isolation Principle

**Critical Rule: Each test must have isolated state**

Every test gets:
1. Fresh QueryClient instance (prevents cache pollution)
2. Reset MSW handlers (clean API mocking state)
3. Cleared mocks (no state from previous tests)

[Source: setupTests.ts:12-17, query-test-wrapper.tsx:30-43]

## Test Infrastructure Setup

### Global Test Configuration

**setupTests.ts Configuration:**

```typescript
// frontend/web-app/src/setupTests.ts:1-22
import '@testing-library/jest-dom';
import { server } from './test-utils/msw-server';

// Establish API mocking before all tests
beforeAll(() => {
  server.listen({
    onUnhandledRequest: 'warn', // Warn about unhandled requests
  });
});

// Reset handlers and mocks after each test
afterEach(() => {
  server.resetHandlers();
  jest.clearAllMocks();
});

// Clean up after all tests
afterAll(() => {
  server.close();
});
```

**Key Configuration Points:**
1. MSW server starts before all tests
2. Handlers reset after each test (isolation)
3. Mocks cleared after each test
4. Server closes after all tests complete

[Source: setupTests.ts:6-22]

### MSW (Mock Service Worker) Setup

**MSW Server Configuration:**

```typescript
// frontend/web-app/src/test-utils/msw-server.ts
import { setupServer } from 'msw/node';
import { rest } from 'msw';

// Default handlers for common API endpoints
export const handlers = [
  rest.get('/api/v1/projects/', (_req, res, ctx) => {
    return res(ctx.json([]));
  }),
];

// Create MSW server instance
export const server = setupServer(...handlers);

// Export utilities for test-specific handlers
export { rest };
```

**MSW Version: v1.x** (for Jest compatibility)

**Why MSW?**
- Intercepts network requests at the network level
- Works with any HTTP client (fetch, axios, etc.)
- No need to mock HTTP libraries
- Same handlers work for both tests and browser development

[Source: msw-server.ts:1-24]

### React Query Test Isolation

**Query Test Wrapper Pattern:**

```typescript
// frontend/web-app/src/test-utils/query-test-wrapper.tsx:30-43
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
```

**Test QueryClient vs Production QueryClient:**

| Setting | Production | Test | Reason |
|---------|-----------|------|--------|
| retry | 2 | false | Fail fast in tests |
| gcTime | 10 minutes | 0 | No cache persistence |
| staleTime | 5 minutes | 0 | Always fetch fresh data |

[Source: query-test-wrapper.tsx:30-73, App.tsx:9-18]

## Test File Organization

### Directory Structure

```
src/
├── components/
│   ├── documentation/
│   │   ├── MarkdownEditor.tsx
│   │   ├── DocumentationView.tsx
│   │   └── __tests__/
│   │       ├── MarkdownEditor.test.tsx
│   │       └── DocumentationView.test.tsx
│   ├── quality/
│   │   ├── MetricsCard.tsx
│   │   └── __tests__/
│   │       └── MetricsCard.test.tsx
│   └── visualization/
│       ├── NetworkGraph.tsx
│       └── __tests__/
│           └── NetworkGraph.test.tsx
├── stores/
│   ├── graphSelectionStore.ts
│   └── __tests__/
│       └── graphSelectionStore.test.ts
└── __tests__/
    └── App.test.tsx        # Top-level integration tests
```

**Naming Convention:**
- Test files: `ComponentName.test.tsx`
- Test directories: `__tests__/`
- Co-locate tests with components in `__tests__/` subdirectory
- Top-level integration tests in `src/__tests__/`

[Source: frontend/web-app/src/ directory structure]

## Integration Test Patterns

### App-Level Integration Tests

**Pattern: Test Real User Flows**

```typescript
// frontend/web-app/src/__tests__/App.test.tsx:66-93
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
```

**Key Patterns:**
1. Override MSW handlers using `server.use()`
2. Render component with test wrapper
3. Use `waitFor()` for async assertions (3s timeout)
4. Assert on final rendered state

[Source: App.test.tsx:66-93]

### Error State Testing

**Pattern: Test API Failures**

```typescript
// App.test.tsx:95-112
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
```

**Error Testing Checklist:**
- [ ] Test 500 server errors
- [ ] Test network failures
- [ ] Test empty states
- [ ] Test retry functionality

[Source: App.test.tsx:95-112]

### Loading State Testing

**Pattern: Delay API Response**

```typescript
// App.test.tsx:53-64
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
```

**Loading State Patterns:**
- Use `ctx.delay('infinite')` for loading states
- Use `ctx.delay(100)` for simulating slow networks

[Source: App.test.tsx:53-64]

### User Interaction Testing

**Pattern: Test User Actions**

```typescript
// App.test.tsx:156-204
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
  await waitFor(() => {
    expect(screen.getByText('Cannot connect to backend')).toBeInTheDocument();
  }, { timeout: 3000 });

  // Mock successful retry
  const mockProjects = [...];
  server.use(
    rest.get('/api/v1/projects/', (req, res, ctx) => {
      return res(ctx.json(mockProjects));
    })
  );

  // Click retry button
  const retryButton = screen.getByRole('button', { name: /retry/i });
  await user.click(retryButton);

  // Should now show ProjectView
  await waitFor(() => {
    expect(screen.getByTestId('project-view')).toBeInTheDocument();
  }, { timeout: 3000 });
});
```

**User Interaction Tools:**
- `userEvent.setup()` - Create user event instance
- `user.click()` - Simulate click
- `user.type()` - Simulate typing
- Always use `await` with userEvent

[Source: App.test.tsx:156-204]

## Component Test Patterns

### Mocking Child Components

**Pattern: Mock Complex Dependencies**

```typescript
// App.test.tsx:36-41
jest.mock('../pages/ProjectView', () => ({
  ProjectView: ({ projectId }: { projectId: string}) => (
    <div data-testid="project-view">ProjectView: {projectId}</div>
  ),
}));
```

**When to Mock:**
- Complex visualizations (D3, Canvas)
- Heavy third-party components
- Components with external dependencies
- Focus testing on component under test

[Source: App.test.tsx:36-41]

### Helper Functions

**Pattern: Extract Common Test Setup**

```typescript
// App.test.tsx:43-50
function renderApp() {
  return renderWithQueryClient(
    <ErrorBoundary>
      <AppContent />
    </ErrorBoundary>
  );
}
```

**Helper Function Benefits:**
- Reduce test duplication
- Ensure consistent setup
- Make tests more readable

[Source: App.test.tsx:43-50]

### Testing Isolated Components

**Pattern: renderWithQueryClient for Components Using React Query**

```typescript
// Example pattern for component tests
import { renderWithQueryClient } from '../test-utils/query-test-wrapper';
import { MyComponent } from './MyComponent';

describe('MyComponent', () => {
  it('renders correctly', () => {
    renderWithQueryClient(<MyComponent />);
    expect(screen.getByText('Hello')).toBeInTheDocument();
  });
});
```

**For components NOT using React Query:**
```typescript
import { render } from '@testing-library/react';

describe('SimpleComponent', () => {
  it('renders correctly', () => {
    render(<SimpleComponent />);
    expect(screen.getByText('Hello')).toBeInTheDocument();
  });
});
```

## Store Testing Patterns

### Zustand Store Tests

**Pattern: Test Store Actions and State**

```typescript
// stores/__tests__/graphSelectionStore.test.ts (example pattern)
import { renderHook, act } from '@testing-library/react';
import { useGraphSelectionStore } from '../graphSelectionStore';

describe('graphSelectionStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    const { result } = renderHook(() => useGraphSelectionStore());
    act(() => {
      result.current.clearSelection();
    });
  });

  it('selects a node', () => {
    const { result } = renderHook(() => useGraphSelectionStore());

    act(() => {
      result.current.selectNode('node-1');
    });

    expect(result.current.selectedNodeIds).toEqual(['node-1']);
  });

  it('toggles node selection', () => {
    const { result } = renderHook(() => useGraphSelectionStore());

    act(() => {
      result.current.toggleNode('node-1');
    });
    expect(result.current.selectedNodeIds).toEqual(['node-1']);

    act(() => {
      result.current.toggleNode('node-1');
    });
    expect(result.current.selectedNodeIds).toEqual([]);
  });
});
```

**Store Testing Checklist:**
- [ ] Test each action
- [ ] Test state updates
- [ ] Test derived state
- [ ] Reset store before each test

[Source: graphSelectionStore.ts:22-41]

## React Testing Library Best Practices

### Query Priority

Use queries in this priority order:

1. **Accessible queries (preferred):**
   - `getByRole` - buttons, headings, etc.
   - `getByLabelText` - form fields
   - `getByPlaceholderText` - inputs
   - `getByText` - non-interactive text

2. **Semantic queries:**
   - `getByAltText` - images
   - `getByTitle` - title attribute

3. **Test IDs (last resort):**
   - `getByTestId` - when other options fail

```typescript
// Good: Use accessible queries (App.test.tsx:111, 192)
expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument();
expect(screen.getByText('Cannot connect to backend')).toBeInTheDocument();

// Last resort: Use test IDs (App.test.tsx:87, 198)
expect(screen.getByTestId('project-view')).toBeInTheDocument();
```

### Async Testing

**waitFor Pattern:**

```typescript
// App.test.tsx:85-90
await waitFor(
  () => {
    expect(screen.getByTestId('project-view')).toBeInTheDocument();
  },
  { timeout: 3000 }
);
```

**Best Practices:**
- Always use `await` with `waitFor`
- Set timeout to 3000ms (3 seconds) for API calls
- Put assertions inside `waitFor` callback
- Use `waitFor` for any async state changes

[Source: App.test.tsx:85-90]

### Screen Queries

**Available Query Variants:**

```typescript
// getBy* - Throws if not found (use for assertions)
expect(screen.getByText('Hello')).toBeInTheDocument();

// queryBy* - Returns null if not found (use for non-existence)
expect(screen.queryByText('Hello')).not.toBeInTheDocument();

// findBy* - Returns promise, waits for element (use for async)
const element = await screen.findByText('Hello');
expect(element).toBeInTheDocument();
```

## Code Coverage Expectations

### Coverage Targets

- **Overall Coverage:** 80% minimum
- **Critical Paths:** 90%+ (authentication, data mutation, error handling)
- **UI Components:** 70%+ (focus on user interactions)

### Coverage Commands

```bash
# Run tests with coverage
npm test -- --coverage

# Run specific test file with coverage
npm test -- ComponentName.test.tsx --coverage

# Generate coverage report
npm test -- --coverage --coverageReporters=html
```

### What NOT to Test

- Third-party library internals
- Trivial getters/setters
- Auto-generated code
- Type definitions
- Constants

## CI/CD Integration

### Test Execution in CI

```yaml
# Example GitHub Actions workflow
test:
  runs-on: ubuntu-latest
  steps:
    - name: Run tests
      run: npm test -- --ci --coverage --maxWorkers=2

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        files: ./coverage/coverage-final.json
```

### CI-Specific Configuration

```typescript
// App.tsx:14 - Disable retries in test environment
retry: process.env.NODE_ENV === 'test' ? false : 2,
```

**CI Environment Variables:**
- `CI=true` - Indicates CI environment
- `NODE_ENV=test` - Test environment

## Testing Best Practices Checklist

**Test Setup:**
- [ ] Use `renderWithQueryClient` for components with React Query
- [ ] Reset MSW handlers after each test (automatic in setupTests.ts)
- [ ] Clear mocks after each test (automatic in setupTests.ts)
- [ ] Create isolated QueryClient per test

**Test Structure:**
- [ ] Use descriptive test names (starts with "it")
- [ ] One assertion per test (when possible)
- [ ] Arrange-Act-Assert pattern
- [ ] Test user behavior, not implementation

**MSW Patterns:**
- [ ] Override handlers with `server.use()` in tests
- [ ] Use `res.once()` for one-time responses
- [ ] Use `ctx.delay()` for loading states
- [ ] Return proper HTTP status codes

**Async Testing:**
- [ ] Use `await waitFor()` for async assertions
- [ ] Set timeout to 3000ms for API calls
- [ ] Use `await userEvent.click()` for interactions
- [ ] Put assertions inside `waitFor` callback

**Accessibility:**
- [ ] Prefer `getByRole` over `getByTestId`
- [ ] Use `getByLabelText` for form inputs
- [ ] Test keyboard navigation
- [ ] Test screen reader compatibility

**Error Testing:**
- [ ] Test API failures (500, 404, network errors)
- [ ] Test empty states
- [ ] Test retry functionality
- [ ] Test error boundaries

## Common Testing Patterns Summary

### 1. Basic Component Test
```typescript
import { render, screen } from '@testing-library/react';
import { MyComponent } from './MyComponent';

it('renders component', () => {
  render(<MyComponent />);
  expect(screen.getByText('Hello')).toBeInTheDocument();
});
```

### 2. Component with React Query
```typescript
import { renderWithQueryClient } from '../test-utils/query-test-wrapper';
import { server, rest } from '../test-utils/msw-server';

it('fetches and displays data', async () => {
  server.use(
    rest.get('/api/data', (req, res, ctx) => {
      return res(ctx.json({ message: 'Success' }));
    })
  );

  renderWithQueryClient(<MyComponent />);

  await waitFor(() => {
    expect(screen.getByText('Success')).toBeInTheDocument();
  }, { timeout: 3000 });
});
```

### 3. User Interaction Test
```typescript
import userEvent from '@testing-library/user-event';

it('handles button click', async () => {
  const user = userEvent.setup();
  render(<MyComponent />);

  const button = screen.getByRole('button', { name: /submit/i });
  await user.click(button);

  expect(screen.getByText('Submitted')).toBeInTheDocument();
});
```

### 4. Store Test
```typescript
import { renderHook, act } from '@testing-library/react';
import { useMyStore } from './myStore';

it('updates store state', () => {
  const { result } = renderHook(() => useMyStore());

  act(() => {
    result.current.updateValue('new value');
  });

  expect(result.current.value).toBe('new value');
});
```

## E2E Testing with Cypress

**Overview:**
End-to-end tests verify the full application stack with real backend interactions. Cypress provides browser automation for testing critical user workflows.

[Source: Story 3.12]

### Cypress Setup

**Installation:**
```bash
cd frontend/web-app
npm install --save-dev cypress --legacy-peer-deps
```

**Configuration (cypress.config.ts):**
```typescript
import { defineConfig } from 'cypress';

export default defineConfig({
  e2e: {
    baseUrl: 'http://localhost:3000',
    env: {
      apiUrl: 'http://localhost:8000',
    },
    viewportWidth: 1920,
    viewportHeight: 1080,
    defaultCommandTimeout: 10000,
    requestTimeout: 30000,
    responseTimeout: 30000,
    video: true,
    screenshotOnRunFailure: true,
    retries: {
      runMode: 2,  // Retry failed tests 2 times in CI
      openMode: 0, // No retries in interactive mode
    },
  },
});
```

**Directory Structure:**
```
frontend/web-app/
├── cypress/
│   ├── e2e/
│   │   ├── application-load.cy.ts      # Workflow 1: App load & project display
│   │   ├── node-interaction.cy.ts      # Workflow 2: Node selection & details
│   │   └── error-handling.cy.ts        # Workflow 3: Error handling & retry
│   ├── fixtures/
│   │   └── test-project.json           # Test data fixtures
│   ├── support/
│   │   ├── commands.ts                 # Custom Cypress commands
│   │   └── e2e.ts                      # Support file
│   └── videos/                         # Test execution videos
└── cypress.config.ts                   # Cypress configuration
```

### Running E2E Tests

**Local Development:**
```bash
# Interactive mode (Cypress UI)
npm run e2e

# Headless mode (terminal only)
npm run e2e:headless

# CI mode (with video and screenshots)
npm run e2e:ci
```

**Prerequisites:**
- Backend API running at `http://localhost:8000`
- Frontend app running at `http://localhost:3000`
- Test database seeded with test data (optional)

### Critical Workflows Tested

**Workflow 1: Application Load & Project Display**
- App loads successfully with loading state
- Default project fetched from backend API
- Network graph renders with topology data
- Graph contains expected nodes and edges

**Workflow 2: Node Selection & Details**
- User clicks nodes in network graph
- Node details panel displays correct information
- Details show IP, hostname, services, vulnerabilities
- State persists when clicking multiple nodes

**Workflow 3: Error Handling & Retry**
- Backend unavailable scenario displays error UI
- Error message: "Cannot connect to backend"
- Retry button successfully reconnects
- App recovers and displays project data

### E2E Test Patterns

**Network Interception:**
```typescript
// Intercept API calls to verify or mock responses
cy.intercept('GET', `${Cypress.env('apiUrl')}/api/v1/projects/`).as('getProjects');

cy.visit('/');

cy.wait('@getProjects').then((interception) => {
  expect(interception.response?.statusCode).to.eq(200);
});
```

**Error State Testing:**
```typescript
// Simulate backend failure
cy.intercept('GET', '/api/v1/projects/', {
  statusCode: 500,
  body: { error: 'Internal Server Error' },
}).as('getProjectsError');

cy.visit('/');

cy.contains('Cannot connect to backend').should('be.visible');
cy.contains('button', /retry/i).click();
```

**Element Selection:**
```typescript
// Wait for elements with appropriate timeouts
cy.get('[data-testid="project-view"]', { timeout: 10000 }).should('exist');

// Find and interact with nodes
cy.get('[data-node-id]').first().click({ force: true });
```

### Custom Commands

**waitForApiReady:**
```typescript
// Custom command to verify API is accessible
cy.waitForApiReady();
```

[Source: cypress/support/commands.ts]

### CI/CD Integration

**GitHub Actions Workflow:**
E2E tests run automatically in CI/CD pipeline after integration tests pass.

**Workflow Steps:**
1. Checkout code
2. Setup Node.js and Python
3. Install dependencies (backend and frontend)
4. Start backend server (background)
5. Build and start frontend (background)
6. Run Cypress tests in headless mode
7. Upload screenshots/videos on failure
8. Generate and upload test reports

**Configuration:**
```yaml
- name: Run E2E tests
  working-directory: ./frontend/web-app
  run: npm run e2e:headless
  env:
    CYPRESS_baseUrl: http://localhost:3000
    CYPRESS_apiUrl: http://localhost:8000
```

[Source: .github/workflows/e2e-tests.yml]

### Test Maintenance

**When to Update E2E Tests:**
- New critical user workflows added
- Breaking changes to UI structure or data attributes
- API endpoints changed
- Error handling behavior modified

**Best Practices:**
- Keep tests focused on critical workflows only
- Use data attributes (`data-testid`, `data-node-id`) for stable selectors
- Add appropriate waits and retries for async operations
- Test both happy path and error scenarios
- Generate artifacts (videos, screenshots) for debugging failures

### Performance Considerations

**Execution Time:**
- Target: < 5 minutes for all 3 workflows
- Each workflow: < 90 seconds
- Acceptable for CI/CD pipeline

**Timeouts:**
- Page load: 30 seconds max
- API requests: 30 seconds max
- Element wait: 10 seconds default

**Retry Logic:**
- Network operations: Retry 2 times in CI
- No retries in local development (fail fast)

### Troubleshooting E2E Tests

**Common Issues:**

1. **Backend not running:**
   - Verify backend is accessible at `http://localhost:8000`
   - Check `curl http://localhost:8000/api/v1/projects/`

2. **Frontend not running:**
   - Verify frontend is accessible at `http://localhost:3000`
   - Check `npm run build && npx serve -s build`

3. **Timeouts:**
   - Increase timeout values in cypress.config.ts
   - Check for slow API responses or network issues

4. **Element not found:**
   - Verify data attributes exist on elements
   - Check for changes in component structure
   - Use Cypress UI to inspect selector issues

5. **Flaky tests:**
   - Add explicit waits for async operations
   - Use network interception to control timing
   - Enable retries in CI mode

## References

**Project Files:**
- [App.test.tsx](frontend/web-app/src/__tests__/App.test.tsx) - Integration test examples
- [query-test-wrapper.tsx](frontend/web-app/src/test-utils/query-test-wrapper.tsx) - React Query test isolation
- [msw-server.ts](frontend/web-app/src/test-utils/msw-server.ts) - MSW setup
- [setupTests.ts](frontend/web-app/src/setupTests.ts) - Global test configuration
- [graphSelectionStore.ts](frontend/web-app/src/stores/graphSelectionStore.ts) - Store pattern example
- [application-load.cy.ts](frontend/web-app/cypress/e2e/application-load.cy.ts) - E2E workflow 1 tests
- [node-interaction.cy.ts](frontend/web-app/cypress/e2e/node-interaction.cy.ts) - E2E workflow 2 tests
- [error-handling.cy.ts](frontend/web-app/cypress/e2e/error-handling.cy.ts) - E2E workflow 3 tests
- [cypress.config.ts](frontend/web-app/cypress.config.ts) - Cypress configuration

**External Documentation:**
- [React Testing Library](https://testing-library.com/docs/react-testing-library/intro/)
- [MSW Documentation](https://mswjs.io/docs/)
- [React Query Testing](https://tanstack.com/query/latest/docs/react/guides/testing)
- [Jest Documentation](https://jestjs.io/docs/getting-started)
- [Testing Library Queries](https://testing-library.com/docs/queries/about)
- [Cypress Documentation](https://docs.cypress.io/)
- [Cypress Best Practices](https://docs.cypress.io/guides/references/best-practices)
