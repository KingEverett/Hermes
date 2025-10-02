/**
 * MSW (Mock Service Worker) server setup for testing
 *
 * Provides API mocking for integration tests without actual network requests.
 * Using MSW v1.x for Jest compatibility.
 */

import { setupServer } from 'msw/node';
import { rest } from 'msw';

// Default handlers for common API endpoints
export const handlers = [
  // GET /api/v1/projects/ - Returns empty array by default
  rest.get('/api/v1/projects/', (_req, res, ctx) => {
    return res(ctx.json([]));
  }),
];

// Create MSW server instance
export const server = setupServer(...handlers);

// Export utilities for test-specific handlers
export { rest };
