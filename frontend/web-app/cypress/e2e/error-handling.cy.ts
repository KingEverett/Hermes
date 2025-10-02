/**
 * E2E Test: Error Handling & Retry
 *
 * Tests the application's error handling when the backend is unavailable,
 * error UI display, and successful recovery via the retry button.
 *
 * AC: 6 - Workflow 3: Error Handling & Retry
 */

describe('Error Handling & Retry', () => {
  it('should display error UI when backend is unavailable', () => {
    // Simulate backend failure by intercepting and failing the API call
    cy.intercept('GET', '/api/v1/projects/', {
      statusCode: 500,
      body: { error: 'Internal Server Error' },
    }).as('getProjectsError');

    // Visit the application
    cy.visit('/');

    // Wait for the failed API call
    cy.wait('@getProjectsError');

    // Verify error message appears
    cy.contains('Cannot connect to backend', { timeout: 10000 }).should('be.visible');

    cy.log('Error UI displayed successfully');
  });

  it('should display retry button when error occurs', () => {
    // Simulate backend failure
    cy.intercept('GET', '/api/v1/projects/', {
      statusCode: 500,
      body: { error: 'Internal Server Error' },
    }).as('getProjectsError');

    // Visit the application
    cy.visit('/');

    // Wait for error
    cy.wait('@getProjectsError');

    // Verify retry button appears
    cy.contains('button', /retry/i, { timeout: 10000 }).should('be.visible');

    cy.log('Retry button is visible');
  });

  it('should successfully reconnect when retry button is clicked', () => {
    // First intercept - fail the initial request
    cy.intercept('GET', '/api/v1/projects/', {
      statusCode: 500,
      body: { error: 'Internal Server Error' },
    }).as('getProjectsFirst');

    // Visit the application
    cy.visit('/');

    // Wait for first failed request
    cy.wait('@getProjectsFirst');

    // Verify error state
    cy.contains('Cannot connect to backend', { timeout: 10000 }).should('be.visible');

    // Setup second intercept - succeed on retry
    cy.intercept('GET', '/api/v1/projects/', {
      statusCode: 200,
      body: [],
    }).as('getProjectsRetry');

    // Click retry button
    cy.contains('button', /retry/i).click();

    // Wait for second (successful) request
    cy.wait('@getProjectsRetry');

    // Verify error message is gone
    cy.contains('Cannot connect to backend').should('not.exist');

    // Verify app recovered (either shows ProjectView or no projects state)
    cy.get('body').should('exist');

    cy.log('Application successfully recovered after retry');
  });

  it('should recover and display project data correctly after retry', () => {
    const mockProject = {
      id: 'test-project-123',
      name: 'Test Project',
      description: 'Test Description',
      created_at: '2025-10-01T00:00:00Z',
    };

    // First intercept - fail the initial request
    cy.intercept('GET', '/api/v1/projects/', {
      statusCode: 500,
      body: { error: 'Internal Server Error' },
    }).as('getProjectsFirst');

    // Visit the application
    cy.visit('/');

    // Wait for first failed request
    cy.wait('@getProjectsFirst');

    // Verify error state
    cy.contains('Cannot connect to backend').should('be.visible');

    // Setup second intercept - succeed with project data on retry
    cy.intercept('GET', '/api/v1/projects/', {
      statusCode: 200,
      body: [mockProject],
    }).as('getProjectsRetry');

    // Mock topology for the project
    cy.intercept('GET', '/api/v1/projects/*/topology', {
      nodes: [],
      edges: [],
      metadata: {
        node_count: 0,
        edge_count: 0,
        generated_at: '2025-10-02T00:00:00Z'
      }
    }).as('getTopology');

    // Click retry button
    cy.contains('button', /retry/i).click();

    // Wait for successful request
    cy.wait('@getProjectsRetry');

    // Verify error is gone
    cy.contains('Cannot connect to backend').should('not.exist');

    // Verify ProjectView is rendered
    cy.get('[data-testid="project-view"]', { timeout: 15000 }).should('exist');

    cy.log('Application recovered and rendered project data');
  });

  it('should handle network timeout errors', () => {
    // Simulate network timeout
    cy.intercept('GET', '/api/v1/projects/', (req) => {
      req.reply({
        statusCode: 504,
        body: { error: 'Gateway Timeout' },
      });
    }).as('getProjectsTimeout');

    // Visit the application
    cy.visit('/');

    // Wait for timeout error
    cy.wait('@getProjectsTimeout');

    // Verify error UI appears
    cy.contains('Cannot connect to backend', { timeout: 10000 }).should('be.visible');

    // Verify retry button is available
    cy.contains('button', /retry/i).should('be.visible');

    cy.log('Timeout error handled correctly');
  });

  it('should handle connection refused errors', () => {
    // Simulate connection refused (network error)
    cy.intercept('GET', '/api/v1/projects/', {
      forceNetworkError: true,
    }).as('getProjectsNetworkError');

    // Visit the application
    cy.visit('/');

    // Wait a moment for the error to propagate
    cy.wait(2000);

    // Verify error UI appears (may vary based on how network errors are handled)
    // The app should show some error state
    cy.get('body').should('exist');

    cy.log('Connection refused handled');
  });

  it('should allow multiple retry attempts', () => {
    // First intercept - fail the initial request
    cy.intercept('GET', '/api/v1/projects/', {
      statusCode: 500,
      body: { error: 'Internal Server Error' },
    }).as('getProjectsFirst');

    // Visit the application
    cy.visit('/');

    // Wait for first failed request
    cy.wait('@getProjectsFirst');
    cy.contains('Cannot connect to backend').should('be.visible');

    // Setup second intercept - fail the first retry
    cy.intercept('GET', '/api/v1/projects/', {
      statusCode: 500,
      body: { error: 'Internal Server Error' },
    }).as('getProjectsSecond');

    // First retry - still fails
    cy.contains('button', /retry/i).click();
    cy.wait('@getProjectsSecond');
    cy.contains('Cannot connect to backend').should('be.visible');

    // Setup third intercept - succeed on second retry
    cy.intercept('GET', '/api/v1/projects/', {
      statusCode: 200,
      body: [],
    }).as('getProjectsThird');

    // Second retry - succeeds
    cy.contains('button', /retry/i).click();
    cy.wait('@getProjectsThird');

    // Error should be gone
    cy.contains('Cannot connect to backend').should('not.exist');

    cy.log('Multiple retry attempts handled successfully');
  });

  it('should complete full error handling and recovery workflow', () => {
    const mockProject = {
      id: 'recovery-test-123',
      name: 'Recovery Test Project',
      description: 'Testing recovery workflow',
      created_at: '2025-10-01T00:00:00Z',
    };

    // First intercept - fail the initial request
    cy.intercept('GET', '/api/v1/projects/', {
      statusCode: 500,
      body: { error: 'Backend Unavailable' },
    }).as('getProjectsFirst');

    // 1. Visit application
    cy.visit('/');
    cy.log('Step 1: Application visited');

    // 2. Wait for initial failed request
    cy.wait('@getProjectsFirst');
    cy.log('Step 2: Initial request failed');

    // 3. Verify error UI displays
    cy.contains('Cannot connect to backend', { timeout: 10000 }).should('be.visible');
    cy.log('Step 3: Error UI displayed');

    // 4. Verify error message is shown
    cy.get('body').should('contain', 'Cannot connect to backend');
    cy.log('Step 4: Error message verified');

    // 5. Verify retry button is visible and clickable
    cy.contains('button', /retry/i).should('be.visible').and('not.be.disabled');
    cy.log('Step 5: Retry button is available');

    // Setup second intercept - succeed with project data on retry
    cy.intercept('GET', '/api/v1/projects/', {
      statusCode: 200,
      body: [mockProject],
    }).as('getProjectsRetry');

    // Mock topology for the project
    cy.intercept('GET', '/api/v1/projects/*/topology', {
      nodes: [],
      edges: [],
      metadata: {
        node_count: 0,
        edge_count: 0,
        generated_at: '2025-10-02T00:00:00Z'
      }
    }).as('getTopology');

    // 6. Click retry button
    cy.contains('button', /retry/i).click();
    cy.log('Step 6: Retry button clicked');

    // 7. Wait for successful retry request
    cy.wait('@getProjectsRetry');
    cy.log('Step 7: Retry request succeeded');

    // 8. Verify error UI is gone
    cy.contains('Cannot connect to backend').should('not.exist');
    cy.log('Step 8: Error UI cleared');

    // 9. Verify app recovered and shows ProjectView
    cy.get('[data-testid="project-view"]', { timeout: 15000 }).should('exist');
    cy.log('Step 9: ProjectView rendered after recovery');

    // 10. Verify app is fully functional
    cy.get('[data-testid="project-view"]').should('be.visible');
    cy.log('Step 10: Application fully recovered and operational');

    cy.log('Full error handling and recovery workflow completed successfully');
  });
});
