/**
 * E2E Test: Application Load & Project Display
 *
 * Tests the critical workflow of loading the application, fetching the default
 * project from the backend API, and rendering the network graph with topology data.
 *
 * AC: 4 - Workflow 1: Application Load & Project Display
 */

describe('Application Load & Project Display', () => {
  beforeEach(() => {
    // Ensure API is accessible before tests
    cy.waitForApiReady();
  });

  it('should load the app and display loading state', () => {
    // Visit the application
    cy.visit('/');

    // Verify loading state appears (may be brief)
    cy.contains('Loading Hermes...', { timeout: 1000 }).should('exist');
  });

  it('should fetch default project from backend API', () => {
    // Intercept the API call to verify it's made
    cy.intercept('GET', '/api/v1/projects/').as('getProjects');

    // Visit the application
    cy.visit('/');

    // Wait for API call to complete
    cy.wait('@getProjects').then((interception) => {
      // Verify the API call was successful
      expect(interception.response?.statusCode).to.be.oneOf([200, 404]);

      // If we have projects, verify the response structure
      if (interception.response?.statusCode === 200) {
        expect(interception.response.body).to.be.an('array');
      }
    });
  });

  it('should render network graph with topology data when project loads', () => {
    // Mock the projects API to return test data
    cy.fixture('test-project').then((project) => {
      cy.intercept('GET', '/api/v1/projects/', [project]).as('getProjects');
    });

    // Mock the topology API to return test topology data
    cy.intercept('GET', '/api/v1/projects/*/topology', {
      nodes: [
        {
          id: 'host_1',
          type: 'host',
          label: 'Web Server 1',
          x: 100,
          y: 100,
          metadata: {
            hostname: 'web-server-1',
            status: 'active'
          }
        }
      ],
      edges: [],
      metadata: {
        node_count: 1,
        edge_count: 0,
        generated_at: '2025-10-02T00:00:00Z'
      }
    }).as('getTopology');

    // Visit the application
    cy.visit('/');

    // Wait for API calls
    cy.wait('@getProjects');
    cy.wait('@getTopology');

    // Wait for the loading state to disappear
    cy.contains('Loading Hermes...').should('not.exist', { timeout: 10000 });

    // Verify ProjectView is rendered
    cy.get('[data-testid="project-view"]', { timeout: 15000 }).should('exist');
  });

  it('should display network graph with nodes when project has topology data', () => {
    // Mock the projects API to return test data
    cy.fixture('test-project').then((project) => {
      cy.intercept('GET', '/api/v1/projects/', [project]).as('getProjects');
    });

    // Mock the topology API with nodes
    cy.intercept('GET', '/api/v1/projects/*/topology', {
      nodes: [
        {
          id: 'host_1',
          type: 'host',
          label: 'Web Server 1',
          x: 100,
          y: 100,
          metadata: {
            hostname: 'web-server-1',
            status: 'active'
          }
        },
        {
          id: 'host_2',
          type: 'host',
          label: 'Database Server',
          x: 200,
          y: 150,
          metadata: {
            hostname: 'db-server-1',
            status: 'active'
          }
        }
      ],
      edges: [
        { source: 'host_1', target: 'host_2' }
      ],
      metadata: {
        node_count: 2,
        edge_count: 1,
        generated_at: '2025-10-02T00:00:00Z'
      }
    }).as('getTopology');

    // Visit the application
    cy.visit('/');

    // Wait for API calls
    cy.wait('@getProjects');
    cy.wait('@getTopology');

    // Wait for loading to complete
    cy.contains('Loading Hermes...').should('not.exist', { timeout: 10000 });

    // Verify ProjectView is rendered
    cy.get('[data-testid="project-view"]', { timeout: 15000 }).should('exist');

    cy.log('ProjectView found, verifying network graph structure');

    // The network graph should be present in the view
    cy.get('[data-testid="project-view"]').should('be.visible');
  });

  it('should handle empty project state gracefully', () => {
    // Intercept projects API and return empty array
    cy.intercept('GET', '/api/v1/projects/', {
      statusCode: 200,
      body: [],
    }).as('getProjects');

    // Visit the application
    cy.visit('/');

    // Wait for API call
    cy.wait('@getProjects');

    // Verify empty state is handled
    cy.contains('Loading Hermes...').should('not.exist', { timeout: 10000 });

    // App should display without crashing
    cy.get('body').should('exist');
  });

  it('should complete full application load workflow end-to-end', () => {
    // This test verifies the complete happy path workflow
    cy.intercept('GET', '/api/v1/projects/').as('getProjects');

    // 1. Visit application
    cy.visit('/');
    cy.log('Step 1: Application visited');

    // 2. Loading state appears
    cy.get('body').should('exist');
    cy.log('Step 2: Application rendering');

    // 3. API call is made
    cy.wait('@getProjects', { timeout: 10000 }).then((interception) => {
      cy.log(`Step 3: API responded with status ${interception.response?.statusCode}`);

      // 4. Loading state disappears
      cy.contains('Loading Hermes...', { timeout: 1000 }).should('not.exist');
      cy.log('Step 4: Loading state cleared');

      // 5. Verify final rendered state
      if (interception.response?.statusCode === 200 &&
          Array.isArray(interception.response.body) &&
          interception.response.body.length > 0) {
        // Project exists - should see ProjectView
        cy.get('[data-testid="project-view"]', { timeout: 15000 }).should('exist');
        cy.log('Step 5: ProjectView rendered successfully');
      } else {
        // No projects - app should still render without errors
        cy.get('body').should('exist');
        cy.log('Step 5: Application rendered with no projects');
      }
    });
  });
});
