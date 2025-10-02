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
    setupNodeEvents(on, config) {
      // implement node event listeners here
    },
  },
});
