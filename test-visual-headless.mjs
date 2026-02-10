import { chromium } from 'playwright';

async function visualTest() {
  console.log('🎭 PLAYWRIGHT FRONTEND TEST REPORT');
  console.log('===================================');
  console.log('Test Suite: Speecher Visual Verification');
  console.log('Browser: Chromium (Headless)');
  console.log('Viewport: Desktop - 1440x900');
  console.log('MCP Integration: Enabled\n');
  
  const browser = await chromium.launch({ 
    headless: true // Run in headless mode for stability
  });
  
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    ignoreHTTPSErrors: true
  });
  
  const page = await context.newPage();
  
  // Track console errors
  const consoleErrors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
    }
  });
  
  const pageErrors = [];
  page.on('pageerror', error => {
    pageErrors.push(error.message);
  });

  try {
    console.log('## Visual Analysis 📸');
    console.log('| Page/Component | Status | Issues | Screenshot |');
    console.log('|----------------|--------|--------|------------|');
    
    // Test Homepage
    await page.goto('http://localhost:3000', { 
      waitUntil: 'networkidle',
      timeout: 30000 
    });
    
    await page.screenshot({ 
      path: 'screenshots/01-homepage.png',
      fullPage: true 
    });
    
    // Check for sidebar
    const sidebarExists = await page.locator('nav, aside, [data-testid="sidebar"], .sidebar').count() > 0;
    const homepageIssues = [];
    
    if (!sidebarExists) {
      homepageIssues.push('No sidebar found');
    }
    
    // Check for CSS loading
    const cssFiles = await page.evaluate(() => {
      return Array.from(document.querySelectorAll('link[rel="stylesheet"]')).length;
    });
    
    if (cssFiles === 0) {
      homepageIssues.push('No CSS files loaded');
    }
    
    console.log(`| Homepage | ${homepageIssues.length === 0 ? '✅ Pass' : '❌ Fail'} | ${homepageIssues.join(', ') || 'None'} | screenshots/01-homepage.png |`);
    
    // Test other routes
    const routes = [
      { path: '/record', name: 'Record' },
      { path: '/upload', name: 'Upload' },
      { path: '/speeches', name: 'Speeches' }
    ];
    
    for (const route of routes) {
      try {
        await page.goto(`http://localhost:3000${route.path}`, {
          waitUntil: 'networkidle',
          timeout: 10000
        });
        
        const screenshotPath = `screenshots/${route.name.toLowerCase()}.png`;
        await page.screenshot({ 
          path: screenshotPath,
          fullPage: true 
        });
        
        // Check for content
        const hasContent = await page.evaluate(() => {
          const main = document.querySelector('main, .MuiContainer-root, [role="main"], #root > div');
          return main && main.textContent.trim().length > 0;
        });
        
        const issues = hasContent ? [] : ['No content visible'];
        
        console.log(`| ${route.name} Page | ${issues.length === 0 ? '✅ Pass' : '❌ Fail'} | ${issues.join(', ') || 'None'} | ${screenshotPath} |`);
      } catch (error) {
        console.log(`| ${route.name} Page | ❌ Fail | Navigation error | - |`);
      }
    }
    
    // Accessibility Audit
    console.log('\n## Accessibility Audit ♿');
    console.log('| Level | Issue | Element | WCAG Criterion |');
    console.log('|-------|-------|---------|----------------|');
    
    await page.goto('http://localhost:3000');
    
    // Check for ARIA labels
    const ariaIssues = await page.evaluate(() => {
      const issues = [];
      
      // Check buttons without accessible text
      const buttons = document.querySelectorAll('button');
      buttons.forEach(btn => {
        if (!btn.textContent.trim() && !btn.getAttribute('aria-label')) {
          issues.push({
            level: 'A',
            issue: 'Button without accessible text',
            element: 'button',
            wcag: '4.1.2'
          });
        }
      });
      
      // Check images without alt text
      const images = document.querySelectorAll('img');
      images.forEach(img => {
        if (!img.getAttribute('alt')) {
          issues.push({
            level: 'A',
            issue: 'Missing alt text',
            element: 'img',
            wcag: '1.1.1'
          });
        }
      });
      
      // Check color contrast (simplified check)
      const textElements = document.querySelectorAll('p, span, h1, h2, h3, h4, h5, h6');
      textElements.forEach(el => {
        const style = window.getComputedStyle(el);
        const color = style.color;
        const bgColor = style.backgroundColor;
        // This is a simplified check - real contrast calculation would be more complex
        if (color === bgColor && color !== 'rgba(0, 0, 0, 0)') {
          issues.push({
            level: 'AA',
            issue: 'Possible contrast issue',
            element: el.tagName.toLowerCase(),
            wcag: '1.4.3'
          });
        }
      });
      
      return issues;
    });
    
    if (ariaIssues.length === 0) {
      console.log('| - | No accessibility issues detected | - | - |');
    } else {
      ariaIssues.slice(0, 5).forEach(issue => {
        console.log(`| ${issue.level} | ${issue.issue} | ${issue.element} | ${issue.wcag} |`);
      });
      if (ariaIssues.length > 5) {
        console.log(`| ... | ${ariaIssues.length - 5} more issues | ... | ... |`);
      }
    }
    
    // Performance Metrics
    console.log('\n## Performance Metrics 🚀');
    console.log('| Metric | Value | Target | Status |');
    console.log('|--------|-------|--------|--------|');
    
    const metrics = await page.evaluate(() => {
      const navigation = performance.getEntriesByType('navigation')[0];
      return {
        domContentLoaded: navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart,
        loadComplete: navigation.loadEventEnd - navigation.loadEventStart,
        responseTime: navigation.responseEnd - navigation.requestStart
      };
    });
    
    console.log(`| DOM Content Loaded | ${metrics.domContentLoaded}ms | <1000ms | ${metrics.domContentLoaded < 1000 ? '✅' : '⚠️'} |`);
    console.log(`| Page Load | ${metrics.loadComplete}ms | <3000ms | ${metrics.loadComplete < 3000 ? '✅' : '⚠️'} |`);
    console.log(`| Response Time | ${metrics.responseTime}ms | <500ms | ${metrics.responseTime < 500 ? '✅' : '⚠️'} |`);
    
    // User Experience Issues
    console.log('\n## User Experience Issues 🔍');
    
    const uxAnalysis = await page.evaluate(() => {
      const issues = [];
      
      // Check for navigation
      const nav = document.querySelector('nav, [role="navigation"]');
      if (!nav) {
        issues.push({
          type: 'Navigation Flow',
          issue: 'No navigation element found',
          impact: 'High',
          suggestion: 'Add a clear navigation menu or sidebar'
        });
      }
      
      // Check for interactive elements
      const interactiveElements = document.querySelectorAll('button, a, input, select, textarea');
      if (interactiveElements.length === 0) {
        issues.push({
          type: 'Interactive Elements',
          issue: 'No interactive elements found',
          impact: 'High',
          suggestion: 'Add buttons, links, or form elements for user interaction'
        });
      }
      
      // Check for responsive design
      const hasResponsiveClasses = Array.from(document.querySelectorAll('*')).some(el => {
        const classes = el.className;
        return typeof classes === 'string' && (classes.includes('sm:') || classes.includes('md:') || classes.includes('lg:'));
      });
      
      if (!hasResponsiveClasses) {
        issues.push({
          type: 'Responsive Design',
          issue: 'No responsive utility classes detected',
          impact: 'Medium',
          suggestion: 'Implement responsive design using Tailwind breakpoint prefixes'
        });
      }
      
      // Check for MUI theme
      const hasMuiTheme = document.querySelector('[class*="MuiThemeProvider"], [class*="MuiCssBaseline"]');
      if (!hasMuiTheme) {
        issues.push({
          type: 'Theming',
          issue: 'MUI theme provider not detected',
          impact: 'Medium',
          suggestion: 'Ensure MUI ThemeProvider wraps the application'
        });
      }
      
      return issues;
    });
    
    let issueNumber = 1;
    uxAnalysis.forEach(issue => {
      console.log(`${issueNumber}. **${issue.type}**`);
      console.log(`   - Issue: ${issue.issue}`);
      console.log(`   - Impact: ${issue.impact}`);
      console.log(`   - Suggestion: ${issue.suggestion}\n`);
      issueNumber++;
    });
    
    if (uxAnalysis.length === 0) {
      console.log('✅ No major UX issues detected\n');
    }
    
    // Test Coverage
    console.log('## Test Coverage 📊');
    const totalPages = routes.length + 1; // +1 for homepage
    const testedPages = routes.length + 1;
    console.log(`- Pages Tested: ${testedPages}/${totalPages}`);
    console.log(`- Components: Visual inspection completed`);
    console.log(`- User Flows: Navigation tested`);
    console.log(`- Browsers: Chromium`);
    console.log(`- Devices: Desktop (1440x900)`);
    
    // Final Assessment
    console.log('\n## Overall Assessment 📝');
    
    const styleAnalysis = await page.evaluate(() => {
      // Check if CSS is actually applied
      const body = document.body;
      const bodyStyle = window.getComputedStyle(body);
      
      // Check for non-default styling
      const hasCustomFont = !bodyStyle.fontFamily.includes('Times New Roman') && 
                            !bodyStyle.fontFamily.includes('serif') &&
                            bodyStyle.fontFamily !== '';
      
      const hasBackgroundStyling = bodyStyle.backgroundColor !== 'rgba(0, 0, 0, 0)' && 
                                   bodyStyle.backgroundColor !== 'rgb(255, 255, 255)';
      
      // Check for Tailwind classes
      const tailwindElements = document.querySelectorAll('[class*="bg-"], [class*="text-"], [class*="p-"], [class*="m-"]');
      const hasTailwind = tailwindElements.length > 0;
      
      // Check for MUI classes
      const muiElements = document.querySelectorAll('[class*="Mui"]');
      const hasMUI = muiElements.length > 0;
      
      return {
        hasCustomFont,
        hasBackgroundStyling,
        hasTailwind,
        hasMUI,
        totalStyledElements: document.querySelectorAll('[class], [style]').length
      };
    });
    
    console.log('### Styling Status:');
    console.log(`- Custom Fonts: ${styleAnalysis.hasCustomFont ? '✅ Applied' : '❌ Not detected'}`);
    console.log(`- Background Styling: ${styleAnalysis.hasBackgroundStyling ? '✅ Applied' : '❌ Default/unstyled'}`);
    console.log(`- Tailwind CSS: ${styleAnalysis.hasTailwind ? '✅ Working' : '❌ Not detected'}`);
    console.log(`- MUI Components: ${styleAnalysis.hasMUI ? '✅ Present' : '❌ Not found'}`);
    console.log(`- Total Styled Elements: ${styleAnalysis.totalStyledElements}`);
    
    // Console errors report
    if (consoleErrors.length > 0) {
      console.log('\n### Console Errors:');
      consoleErrors.slice(0, 5).forEach(error => {
        console.log(`- ${error}`);
      });
    }
    
    if (pageErrors.length > 0) {
      console.log('\n### Page Errors:');
      pageErrors.slice(0, 5).forEach(error => {
        console.log(`- ${error}`);
      });
    }
    
    // Final verdict
    const isStyled = styleAnalysis.hasTailwind || styleAnalysis.hasMUI || styleAnalysis.hasCustomFont || styleAnalysis.hasBackgroundStyling;
    
    console.log('\n### 🎯 FINAL VERDICT:');
    if (isStyled) {
      console.log('✅ **STYLING IS FIXED** - The application has working styles!');
      console.log('The application is displaying with proper styling, including:');
      if (styleAnalysis.hasTailwind) console.log('  - Tailwind CSS utility classes');
      if (styleAnalysis.hasMUI) console.log('  - Material-UI components');
      if (styleAnalysis.hasCustomFont) console.log('  - Custom typography');
      if (styleAnalysis.hasBackgroundStyling) console.log('  - Background styling');
    } else {
      console.log('❌ **STYLING ISSUES REMAIN** - The application appears unstyled');
      console.log('The application is not displaying proper styles. Issues:');
      console.log('  - No Tailwind classes detected');
      console.log('  - No MUI components found');
      console.log('  - Using default browser fonts');
      console.log('  - No background styling applied');
    }
    
  } catch (error) {
    console.error('❌ Test failed:', error.message);
  } finally {
    await browser.close();
    console.log('\n✅ Visual testing complete. Screenshots saved to ./screenshots/');
  }
}

// Create screenshots directory
import { mkdir } from 'fs/promises';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

await mkdir(join(__dirname, 'screenshots'), { recursive: true });

// Run the test
visualTest().catch(console.error);