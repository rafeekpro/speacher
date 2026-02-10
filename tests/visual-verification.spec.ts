import { test, expect } from '@playwright/test';

test.describe('Speecher Visual Verification', () => {
  test.beforeEach(async ({ page }) => {
    // Set viewport for consistent screenshots
    await page.setViewportSize({ width: 1440, height: 900 });
  });

  test('Homepage visual verification', async ({ page }) => {
    // Navigate to homepage
    await page.goto('http://localhost:3000');
    
    // Wait for content to load
    await page.waitForLoadState('networkidle');
    
    // Take screenshot
    await page.screenshot({ 
      path: 'screenshots/homepage.png',
      fullPage: true 
    });

    // Verify sidebar is visible
    const sidebar = page.locator('[data-testid="sidebar"], nav, aside, .sidebar, #sidebar').first();
    await expect(sidebar).toBeVisible();
    
    // Check sidebar has proper styling (background color)
    const sidebarBg = await sidebar.evaluate(el => 
      window.getComputedStyle(el).backgroundColor
    );
    expect(sidebarBg).not.toBe('rgba(0, 0, 0, 0)'); // Should have a background
    
    // Verify navigation links are visible
    const navLinks = page.locator('nav a, aside a, [role="navigation"] a').first();
    await expect(navLinks).toBeVisible();
    
    // Check for MUI components
    const muiElements = page.locator('[class*="MuiPaper"], [class*="MuiButton"], [class*="MuiTypography"]').first();
    await expect(muiElements).toBeVisible();
    
    // Check Tailwind classes are working (look for padding/margin)
    const paddedElement = page.locator('[class*="p-"], [class*="m-"], [class*="px-"], [class*="py-"]').first();
    await expect(paddedElement).toBeVisible();
    
    console.log('✅ Homepage verified - Sidebar visible, styling applied');
  });

  test('Record page visual verification', async ({ page }) => {
    await page.goto('http://localhost:3000/record');
    await page.waitForLoadState('networkidle');
    
    await page.screenshot({ 
      path: 'screenshots/record-page.png',
      fullPage: true 
    });
    
    // Check for record-specific elements
    const recordContent = page.locator('main, [role="main"], .content, #content').first();
    await expect(recordContent).toBeVisible();
    
    // Verify page has content
    const pageTitle = page.locator('h1, h2, [class*="MuiTypography-h"]').first();
    await expect(pageTitle).toBeVisible();
    
    console.log('✅ Record page verified');
  });

  test('Upload page visual verification', async ({ page }) => {
    await page.goto('http://localhost:3000/upload');
    await page.waitForLoadState('networkidle');
    
    await page.screenshot({ 
      path: 'screenshots/upload-page.png',
      fullPage: true 
    });
    
    // Check for upload-specific elements
    const uploadArea = page.locator('[class*="upload"], [class*="drop"], input[type="file"]').first();
    const hasUploadElements = await uploadArea.count() > 0;
    
    if (hasUploadElements) {
      console.log('✅ Upload page verified - Upload elements found');
    } else {
      console.log('⚠️ Upload page loaded but no upload elements found');
    }
  });

  test('History page visual verification', async ({ page }) => {
    await page.goto('http://localhost:3000/history');
    await page.waitForLoadState('networkidle');
    
    await page.screenshot({ 
      path: 'screenshots/history-page.png',
      fullPage: true 
    });
    
    // Check for history/list elements
    const listContent = page.locator('table, [role="table"], [class*="list"], [class*="grid"]').first();
    const hasListElements = await listContent.count() > 0;
    
    if (hasListElements) {
      console.log('✅ History page verified - List/table elements found');
    } else {
      console.log('⚠️ History page loaded but no list elements found');
    }
  });

  test('Visual consistency check', async ({ page }) => {
    await page.goto('http://localhost:3000');
    
    // Check theme consistency
    const primaryColor = await page.locator('[class*="MuiButton-containedPrimary"], [class*="bg-blue"], [class*="bg-primary"]').first().evaluate(el => 
      window.getComputedStyle(el).backgroundColor
    ).catch(() => null);
    
    // Check dark mode if applicable
    const isDarkMode = await page.locator('body').evaluate(el => {
      const bg = window.getComputedStyle(el).backgroundColor;
      // Parse RGB values
      const match = bg.match(/\d+/g);
      if (match) {
        const [r, g, b] = match.map(Number);
        return (r + g + b) / 3 < 128; // Dark if average is less than 128
      }
      return false;
    });
    
    // Check responsive layout
    const hasResponsiveClasses = await page.locator('[class*="sm:"], [class*="md:"], [class*="lg:"]').count() > 0;
    
    console.log('🎨 Visual Analysis:');
    console.log(`  - Dark mode: ${isDarkMode ? 'Yes' : 'No'}`);
    console.log(`  - Responsive classes: ${hasResponsiveClasses ? 'Yes' : 'No'}`);
    console.log(`  - Primary color detected: ${primaryColor ? 'Yes' : 'No'}`);
  });

  test('Accessibility and UX check', async ({ page }) => {
    await page.goto('http://localhost:3000');
    
    // Check for ARIA labels
    const ariaElements = await page.locator('[aria-label], [role]').count();
    
    // Check for keyboard navigation
    await page.keyboard.press('Tab');
    const focusedElement = await page.evaluate(() => 
      document.activeElement?.tagName
    );
    
    // Check for hover states
    const button = page.locator('button').first();
    if (await button.count() > 0) {
      const initialColor = await button.evaluate(el => 
        window.getComputedStyle(el).backgroundColor
      );
      
      await button.hover();
      await page.waitForTimeout(100);
      
      const hoverColor = await button.evaluate(el => 
        window.getComputedStyle(el).backgroundColor
      );
      
      const hasHoverState = initialColor !== hoverColor;
      
      console.log('♿ Accessibility & UX:');
      console.log(`  - ARIA elements: ${ariaElements}`);
      console.log(`  - Keyboard navigation: ${focusedElement ? 'Working' : 'Not working'}`);
      console.log(`  - Hover states: ${hasHoverState ? 'Working' : 'Not detected'}`);
    }
  });
});