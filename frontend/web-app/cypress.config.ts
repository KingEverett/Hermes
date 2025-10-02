import { defineConfig } from 'cypress';

export default defineConfig({
  e2e: {
    baseUrl: 'http://localhost:3000',
    env: {
      apiUrl: 'http://localhost:8000',
    },
    viewportWidth: 1920,
    viewportHeight: 1080,
    defaultCommandTimeout: 15000,  // Increased from 10s
    requestTimeout: 30000,
    responseTimeout: 30000,
    pageLoadTimeout: 60000,        // Added page load timeout
    video: true,
    screenshotOnRunFailure: true,
    retries: {
      runMode: 2,  // Retry failed tests 2 times in CI
      openMode: 0, // No retries in interactive mode
    },
    // Memory management for CI stability
    experimentalMemoryManagement: true,
    numTestsKeptInMemory: 1,
    chromeWebSecurity: false,
    setupNodeEvents(on, config) {
      // Memory cleanup between tests
      on('after:spec', () => {
        if (global.gc) {
          global.gc();
        }
      });
    },
  },
});
