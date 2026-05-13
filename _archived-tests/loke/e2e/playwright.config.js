// @ts-check
const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: '.',
  timeout: 30000,
  expect: { timeout: 5000 },
  fullyParallel: true,
  reporter: [['list'], ['json', { outputFile: 'test-results.json' }]],
  use: {
    headless: true,
    viewport: { width: 1280, height: 800 },
  },
  projects: [
    {
      name: 'loke',
      testMatch: 'loke.spec.js',
      use: { baseURL: 'http://127.0.0.1:11430' },
    },
    {
      name: 'moke',
      testMatch: 'moke.spec.js',
      use: { baseURL: 'http://localhost:11432' },
    },
  ],
});
