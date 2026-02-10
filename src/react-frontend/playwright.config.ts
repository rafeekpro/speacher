import { defineConfig, devices } from '@playwright/test';
import path from 'path';

// Environment detection
const isCI = !!process.env.CI;
const isGitHubActions = !!process.env.GITHUB_ACTIONS;
const isKubernetes = !!process.env.KUBERNETES_SERVICE_HOST;

// Dynamic port allocation to avoid conflicts
const DEFAULT_PORT = 3000;
const CI_PORT_BASE = 4000; // Use different port range in CI
const getAvailablePort = () => {
  if (isCI) {
    // In CI, use a port range less likely to conflict
    const randomOffset = Math.floor(Math.random() * 1000);
    return CI_PORT_BASE + randomOffset;
  }
  return process.env.PORT ? parseInt(process.env.PORT, 10) : DEFAULT_PORT;
};

const PORT = getAvailablePort();
const BASE_URL = process.env.BASE_URL || `http://localhost:${PORT}`;

// Debug logging for troubleshooting
if (isCI) {
  console.log(`🎭 Playwright Config - CI Environment Detected`);
  console.log(`   Environment: CI=${process.env.CI}, GitHub Actions=${isGitHubActions}, Kubernetes=${isKubernetes}`);
  console.log(`   Port: ${PORT}, Base URL: ${BASE_URL}`);
  console.log(`   Worker count: 1 (CI optimization)`);
}

export default defineConfig({
  testDir: './tests',
  testMatch: ['**/*.spec.ts'],
  fullyParallel: false, // Visual tests should run sequentially for consistency
  forbidOnly: !!process.env.CI,
  retries: isCI ? 2 : 0,
  workers: isCI ? 1 : undefined, // Single worker in CI for consistency, auto-detect locally
  reporter: [
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
    ['json', { outputFile: 'test-results/results.json' }],
    ['junit', { outputFile: 'test-results/junit.xml' }],
    ['list']
  ],

  use: {
    baseURL: BASE_URL,
    trace: 'retain-on-failure',
    screenshot: {
      mode: 'only-on-failure',
      fullPage: true
    },
    video: 'retain-on-failure',
    actionTimeout: 10000,
    navigationTimeout: 30000,

    // Visual testing specific settings
    ignoreHTTPSErrors: true,
    locale: 'en-US',
    timezoneId: 'America/New_York',
    
    // Consistent viewport for visual tests
    viewport: { width: 1280, height: 720 },
  },

  projects: [
    {
      name: 'chromium',
      use: { 
        ...devices['Desktop Chrome'],
        // Force consistent rendering
        deviceScaleFactor: 1,
        hasTouch: false,
        isMobile: false,
        // CI-specific optimizations
        launchOptions: {
          args: [
            '--disable-animations', 
            '--disable-web-security',
            '--disable-features=TranslateUI',
            '--disable-ipc-flooding-protection',
            ...(isCI ? [
              '--no-sandbox',
              '--disable-setuid-sandbox',
              '--disable-dev-shm-usage',
              '--disable-accelerated-2d-canvas',
              '--no-first-run',
              '--no-zygote',
              '--single-process',
              '--disable-gpu',
              '--disable-background-timer-throttling',
              '--disable-backgrounding-occluded-windows',
              '--disable-renderer-backgrounding'
            ] : [])
          ],
        },
      },
    },
    // Only include other browsers in non-CI environments
    ...(isCI ? [] : [
      {
        name: 'firefox',
        use: { 
          ...devices['Desktop Firefox'],
          deviceScaleFactor: 1,
          hasTouch: false,
          isMobile: false,
        },
      },
      {
        name: 'webkit',
        use: { 
          ...devices['Desktop Safari'],
          deviceScaleFactor: 1,
          hasTouch: false,
          isMobile: false,
        },
      },
      {
        name: 'mobile-chrome',
        use: { 
          ...devices['Pixel 5'],
          deviceScaleFactor: 2,
        },
      },
      {
        name: 'mobile-safari',
        use: { 
          ...devices['iPhone 13'],
          deviceScaleFactor: 3,
        },
      },
      {
        name: 'tablet',
        use: { 
          ...devices['iPad (gen 7)'],
          deviceScaleFactor: 2,
        },
      },
    ]),
  ],

  webServer: {
    command: isCI 
      ? `npm run build && npx serve -s build -l ${PORT}`
      : `PORT=${PORT} npm start`,
    url: BASE_URL,
    reuseExistingServer: true, // Always reuse existing server to avoid conflicts
    timeout: isCI ? 180000 : 120000, // More time for build in CI
    stdout: 'pipe',
    stderr: 'pipe',
    env: {
      ...process.env,
      BROWSER: 'none', // Prevent react-scripts from opening browser
      HOST: '0.0.0.0', // Bind to all interfaces
      PORT: String(PORT), // Ensure port is passed to the server
    },
    ignoreHTTPSErrors: true,
  },

  // Visual testing specific configuration
  expect: {
    // Timeout for assertions
    timeout: 10000,

    // Visual comparison settings
    toHaveScreenshot: {
      // Maximum difference in pixels
      maxDiffPixels: 100,
      
      // Threshold for pixel difference (0-1)
      threshold: 0.2,
      
      // Animation handling
      animations: 'disabled',
      
      // Consistent screenshot naming
      scale: 'css',
    },
  },

  // Output directories
  outputDir: 'test-results',
  
  // Screenshot storage
  snapshotDir: './tests/visual/__screenshots__',
  snapshotPathTemplate: '{snapshotDir}/{testFileDir}/{testFileName}-snapshots/{arg}-{projectName}-{platform}{ext}',
});