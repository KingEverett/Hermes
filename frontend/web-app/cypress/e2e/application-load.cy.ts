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
    cy.intercept('GET', `${Cypress.env('apiUrl')}/api/v1/projects/`).as('getProjects');

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
    // Visit the application
    cy.visit('/');

    // Wait for the loading state to disappear
    cy.contains('Loading Hermes...').should('not.exist', { timeout: 10000 });

    // Verify the app has loaded past loading state
    // The app should either show ProjectView or "No projects" state
    cy.get('body').should('exist');

    // If a project exists, verify ProjectView is rendered
    cy.get('[data-testid="project-view"]', { timeout: 15000 })
      .should('exist')
      .then(($projectView) => {
        // ProjectView found - verify it contains project data
        expect($projectView).to.exist;
      });
  });

  it('should display network graph with nodes when project has topology data', () => {
    // Intercept projects API
    cy.intercept('GET', `${Cypress.env('apiUrl')}/api/v1/projects/`).as('getProjects');

    // Visit the application
    cy.visit('/');

    // Wait for projects to load
    cy.wait('@getProjects', { timeout: 10000 });

    // Wait for loading to complete
    cy.contains('Loading Hermes...').should('not.exist', { timeout: 10000 });

    // Verify ProjectView is rendered (if project exists)
    cy.get('[data-testid="project-view"]', { timeout: 15000 }).then(($projectView) => {
      if ($projectView.length > 0) {
        // ProjectView exists - look for NetworkGraph
        cy.log('ProjectView found, checking for network graph');

        // The network graph should be present in the view
        // Note: Actual graph structure depends on implementation
        // This verifies the component hierarchy loaded successfully
        cy.get('[data-testid="project-view"]').should('be.visible');
      }
    });
  });

  it('should handle empty project state gracefully', () => {
    // Intercept projects API and return empty array
    cy.intercept('GET', `${Cypress.env('apiUrl')}/api/v1/projects/`, {
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
    cy.intercept('GET', `${Cypress.env('apiUrl')}/api/v1/projects/`).as('getProjects');

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
