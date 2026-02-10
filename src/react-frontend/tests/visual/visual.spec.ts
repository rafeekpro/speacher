import { test, expect, Page } from '@playwright/test';
import fs from 'fs';
import path from 'path';

// Routes to test - this should be kept in sync with your application routes
const ROUTES_TO_TEST = [
  { path: '/', name: 'home', waitFor: 'text=Welcome' },
  { path: '/dashboard', name: 'dashboard', waitFor: '[data-testid="dashboard"]' },
  { path: '/projects', name: 'projects', waitFor: '[data-testid="projects-list"]' },
  { path: '/settings', name: 'settings', waitFor: 'text=Settings' },
  { path: '/profile', name: 'profile', waitFor: '[data-testid="profile"]' },
  { path: '/help', name: 'help', waitFor: 'text=Help' },
  { path: '/about', name: 'about', waitFor: 'text=About' },
  { path: '/404', name: 'not-found', waitFor: 'text=404' },
];

// Visual testing configuration
const VISUAL_CONFIG = {
  // Wait for network to be idle
  waitForLoadState: 'networkidle' as const,
  
  // Wait for fonts to load
  waitForFonts: true,
  
  // Additional wait to ensure all async operations complete
  additionalWait: 1000,
  
  // Mask dynamic content
  maskSelectors: [
    '[data-testid="timestamp"]',
    '[data-testid="dynamic-content"]',
    '.date-time',
    '.loading-spinner',
    'time',
  ],
  
  // Clip to viewport for consistent results
  clip: { x: 0, y: 0, width: 1280, height: 720 },
};

// Helper to wait for page to be fully loaded
async function waitForPageReady(page: Page) {
  // Wait for network idle
  await page.waitForLoadState(VISUAL_CONFIG.waitForLoadState);
  
  // Wait for fonts to load
  if (VISUAL_CONFIG.waitForFonts) {
    await page.evaluate(() => document.fonts.ready);
  }
  
  // Additional wait for any animations or async operations
  await page.waitForTimeout(VISUAL_CONFIG.additionalWait);
  
  // Ensure no loading indicators are visible
  await page.waitForSelector('.loading', { state: 'hidden' }).catch(() => {});
  await page.waitForSelector('[data-loading="true"]', { state: 'hidden' }).catch(() => {});
}

// Helper to mask dynamic content
async function maskDynamicContent(page: Page) {
  for (const selector of VISUAL_CONFIG.maskSelectors) {
    await page.locator(selector).evaluateAll((elements) => {
      elements.forEach(el => {
        (el as HTMLElement).style.visibility = 'hidden';
      });
    }).catch(() => {}); // Ignore if selector doesn't exist
  }
}

// Helper to prepare page for screenshot
async function preparePageForScreenshot(page: Page) {
  // Disable animations
  await page.addStyleTag({
    content: `
      *, *::before, *::after {
        animation-duration: 0s !important;
        animation-delay: 0s !important;
        transition-duration: 0s !important;
        transition-delay: 0s !important;
      }
    `
  });
  
  // Hide scrollbars
  await page.addStyleTag({
    content: `
      ::-webkit-scrollbar { display: none !important; }
      * { scrollbar-width: none !important; }
    `
  });
  
  // Ensure consistent focus states
  await page.evaluate(() => {
    document.activeElement?.blur();
  });
}

test.describe('Visual Regression Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Set consistent conditions
    await page.setViewportSize({ width: 1280, height: 720 });
    
    // Mock date/time for consistency
    await page.addInitScript(() => {
      const constantDate = new Date('2024-01-01T12:00:00.000Z');
      Date = class extends Date {
        constructor(...args: any[]) {
          if (args.length === 0) {
            super(constantDate);
          } else {
            // @ts-ignore
            super(...args);
          }
        }
        static now() {
          return constantDate.getTime();
        }
      } as any;
    });
  });

  // Test each route
  for (const route of ROUTES_TO_TEST) {
    test(`Visual test: ${route.name} page (${route.path})`, async ({ page }) => {
      // Navigate to route
      await page.goto(route.path);
      
      // Wait for specific content if provided
      if (route.waitFor) {
        await page.waitForSelector(route.waitFor, { timeout: 10000 }).catch(() => {
          console.warn(`Warning: Could not find selector "${route.waitFor}" for ${route.name}`);
        });
      }
      
      // Prepare page for screenshot
      await preparePageForScreenshot(page);
      await waitForPageReady(page);
      await maskDynamicContent(page);
      
      // Take full page screenshot
      await expect(page).toHaveScreenshot(`${route.name}-full-page.png`, {
        fullPage: true,
        animations: 'disabled',
        mask: await page.locator(VISUAL_CONFIG.maskSelectors.join(', ')).all().catch(() => []),
      });
      
      // Take viewport screenshot
      await expect(page).toHaveScreenshot(`${route.name}-viewport.png`, {
        fullPage: false,
        animations: 'disabled',
        clip: VISUAL_CONFIG.clip,
      });
    });
  }

  test.describe('Component Visual Tests', () => {
    test('Header component', async ({ page }) => {
      await page.goto('/');
      await preparePageForScreenshot(page);
      await waitForPageReady(page);
      
      const header = page.locator('header, [role="banner"], [data-testid="header"]').first();
      await expect(header).toBeVisible();
      await expect(header).toHaveScreenshot('header-component.png');
    });

    test('Footer component', async ({ page }) => {
      await page.goto('/');
      await preparePageForScreenshot(page);
      await waitForPageReady(page);
      
      const footer = page.locator('footer, [role="contentinfo"], [data-testid="footer"]').first();
      await expect(footer).toBeVisible();
      await expect(footer).toHaveScreenshot('footer-component.png');
    });

    test('Navigation component', async ({ page }) => {
      await page.goto('/');
      await preparePageForScreenshot(page);
      await waitForPageReady(page);
      
      const nav = page.locator('nav, [role="navigation"], [data-testid="navigation"]').first();
      await expect(nav).toBeVisible();
      await expect(nav).toHaveScreenshot('navigation-component.png');
    });

    test('Sidebar component', async ({ page }) => {
      await page.goto('/dashboard');
      await preparePageForScreenshot(page);
      await waitForPageReady(page);
      
      const sidebar = page.locator('aside, [role="complementary"], [data-testid="sidebar"]').first();
      if (await sidebar.isVisible()) {
        await expect(sidebar).toHaveScreenshot('sidebar-component.png');
      }
    });
  });

  test.describe('Responsive Visual Tests', () => {
    const viewports = [
      { width: 375, height: 667, name: 'mobile-small' },
      { width: 768, height: 1024, name: 'tablet' },
      { width: 1024, height: 768, name: 'desktop-small' },
      { width: 1920, height: 1080, name: 'desktop-large' },
    ];

    for (const viewport of viewports) {
      test(`Homepage at ${viewport.name} (${viewport.width}x${viewport.height})`, async ({ page }) => {
        await page.setViewportSize({ width: viewport.width, height: viewport.height });
        await page.goto('/');
        await preparePageForScreenshot(page);
        await waitForPageReady(page);
        await maskDynamicContent(page);
        
        await expect(page).toHaveScreenshot(`home-${viewport.name}.png`, {
          fullPage: false,
          animations: 'disabled',
        });
      });
    }
  });

  test.describe('Interactive State Visual Tests', () => {
    test('Button hover states', async ({ page }) => {
      await page.goto('/');
      await preparePageForScreenshot(page);
      await waitForPageReady(page);
      
      const button = page.locator('button, [role="button"]').first();
      if (await button.isVisible()) {
        // Normal state
        await expect(button).toHaveScreenshot('button-normal.png');
        
        // Hover state
        await button.hover();
        await page.waitForTimeout(100);
        await expect(button).toHaveScreenshot('button-hover.png');
        
        // Focus state
        await button.focus();
        await page.waitForTimeout(100);
        await expect(button).toHaveScreenshot('button-focus.png');
      }
    });

    test('Form input states', async ({ page }) => {
      await page.goto('/');
      await preparePageForScreenshot(page);
      await waitForPageReady(page);
      
      const input = page.locator('input[type="text"], input[type="email"]').first();
      if (await input.isVisible()) {
        // Normal state
        await expect(input).toHaveScreenshot('input-normal.png');
        
        // Focus state
        await input.focus();
        await page.waitForTimeout(100);
        await expect(input).toHaveScreenshot('input-focus.png');
        
        // Filled state
        await input.fill('Test content');
        await page.waitForTimeout(100);
        await expect(input).toHaveScreenshot('input-filled.png');
      }
    });
  });

  test.describe('Dark Mode Visual Tests', () => {
    test('Toggle dark mode', async ({ page }) => {
      await page.goto('/');
      await preparePageForScreenshot(page);
      await waitForPageReady(page);
      
      // Check for dark mode toggle
      const darkModeToggle = page.locator('[data-testid="dark-mode-toggle"], [aria-label*="dark"], [aria-label*="theme"]').first();
      
      if (await darkModeToggle.isVisible()) {
        // Light mode screenshot
        await expect(page).toHaveScreenshot('home-light-mode.png', {
          fullPage: false,
          animations: 'disabled',
        });
        
        // Toggle to dark mode
        await darkModeToggle.click();
        await waitForPageReady(page);
        
        // Dark mode screenshot
        await expect(page).toHaveScreenshot('home-dark-mode.png', {
          fullPage: false,
          animations: 'disabled',
        });
      }
    });
  });

  test.describe('Accessibility Visual Tests', () => {
    test('High contrast mode', async ({ page }) => {
      // Inject high contrast CSS
      await page.goto('/');
      await page.addStyleTag({
        content: `
          * {
            filter: contrast(2) !important;
          }
        `
      });
      await preparePageForScreenshot(page);
      await waitForPageReady(page);
      
      await expect(page).toHaveScreenshot('home-high-contrast.png', {
        fullPage: false,
        animations: 'disabled',
      });
    });

    test('Focus indicators visible', async ({ page }) => {
      await page.goto('/');
      await preparePageForScreenshot(page);
      await waitForPageReady(page);
      
      // Tab through interactive elements
      for (let i = 0; i < 5; i++) {
        await page.keyboard.press('Tab');
        await page.waitForTimeout(100);
      }
      
      await expect(page).toHaveScreenshot('focus-indicators.png', {
        fullPage: false,
        animations: 'disabled',
      });
    });
  });
});

// Critical failure detection test
test.describe('Critical Visual Failures', () => {
  test('Detect layout breaks', async ({ page }) => {
    await page.goto('/');
    await preparePageForScreenshot(page);
    await waitForPageReady(page);
    
    // Check for overlapping elements
    const hasOverlaps = await page.evaluate(() => {
      const elements = document.querySelectorAll('*');
      for (let i = 0; i < elements.length; i++) {
        for (let j = i + 1; j < elements.length; j++) {
          const rect1 = elements[i].getBoundingClientRect();
          const rect2 = elements[j].getBoundingClientRect();
          
          // Check if elements overlap (excluding parent-child relationships)
          if (!elements[i].contains(elements[j]) && !elements[j].contains(elements[i])) {
            const overlap = !(rect1.right < rect2.left || 
                            rect2.right < rect1.left || 
                            rect1.bottom < rect2.top || 
                            rect2.bottom < rect1.top);
            if (overlap && rect1.width > 0 && rect1.height > 0 && rect2.width > 0 && rect2.height > 0) {
              return true;
            }
          }
        }
      }
      return false;
    });
    
    expect(hasOverlaps).toBe(false);
  });

  test('Detect missing images', async ({ page }) => {
    await page.goto('/');
    await waitForPageReady(page);
    
    const brokenImages = await page.evaluate(() => {
      const images = Array.from(document.querySelectorAll('img'));
      return images.filter(img => !img.complete || img.naturalWidth === 0).map(img => img.src);
    });
    
    expect(brokenImages).toHaveLength(0);
  });

  test('Detect text overflow', async ({ page }) => {
    await page.goto('/');
    await waitForPageReady(page);
    
    const hasTextOverflow = await page.evaluate(() => {
      const elements = document.querySelectorAll('*');
      for (const element of elements) {
        if (element.scrollWidth > element.clientWidth || 
            element.scrollHeight > element.clientHeight) {
          const styles = window.getComputedStyle(element);
          if (styles.overflow !== 'auto' && styles.overflow !== 'scroll') {
            return true;
          }
        }
      }
      return false;
    });
    
    expect(hasTextOverflow).toBe(false);
  });
});

// Export test metadata for reporting
export const visualTestMetadata = {
  routes: ROUTES_TO_TEST,
  config: VISUAL_CONFIG,
  timestamp: new Date().toISOString(),
  version: '1.0.0',
};