module.exports = {
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/src/setupTests.ts'],
  transformIgnorePatterns: [
    'node_modules/(?!(@uiw|rehype-prism-plus|unist-util-visit|hast-util-to-string|unist-util-filter|parse-numeric-range|refractor)/)',
  ],
  moduleNameMapper: {
    '^@uiw/react-md-editor$': '<rootDir>/src/__mocks__/@uiw/react-md-editor.tsx',
  },
  testTimeout: 10000,
  collectCoverageFrom: [
    'src/**/*.{ts,tsx}',
    '!src/**/*.d.ts',
    '!src/test-utils/**',
    '!src/__mocks__/**',
  ],
};
