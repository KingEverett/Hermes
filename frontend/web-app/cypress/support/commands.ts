/// <reference types="cypress" />

// ***********************************************
// This example commands.ts shows you how to
// create various custom commands and overwrite
// existing commands.
//
// For more comprehensive examples of custom
// commands please read more here:
// https://on.cypress.io/custom-commands
// ***********************************************

// Custom command to wait for API requests to complete
Cypress.Commands.add('waitForApiReady', () => {
  cy.request({
    url: `${Cypress.env('apiUrl')}/api/v1/projects/`,
    failOnStatusCode: false,
  }).then((response) => {
    expect(response.status).to.be.oneOf([200, 404]);
  });
});

declare global {
  namespace Cypress {
    interface Chainable {
      /**
       * Custom command to wait for the API to be ready
       * @example cy.waitForApiReady()
       */
      waitForApiReady(): Chainable<void>;
    }
  }
}

export {};
