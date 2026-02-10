import { chromium } from 'playwright';

async function visualTest() {
  console.log('Starting visual test of Speecher application...\n');
  
  const browser = await chromium.launch({ 
    headless: false,
    devtools: true 
  });
  
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    ignoreHTTPSErrors: true
  });
  
  const page = await context.newPage();
  
  // Enable console logging
  page.on('console', msg => {
    if (msg.type() === 'error') {
      console.log('❌ Console Error:', msg.text());
    }
  });
  
  page.on('pageerror', error => {
    console.log('❌ Page Error:', error.message);
  });
  
  page.on('requestfailed', request => {
    console.log('❌ Request Failed:', request.url(), '-', request.failure().errorText);
  });

  try {
    console.log('📍 1. Navigating to homepage (http://localhost:3000)...');
    await page.goto('http://localhost:3000', { 
      waitUntil: 'networkidle',
      timeout: 30000 
    });
    
    // Take screenshot of homepage
    await page.screenshot({ 
      path: 'screenshots/01-homepage.png',
      fullPage: true 
    });
    console.log('✅ Homepage screenshot saved');
    
    // Check for CSS files
    const cssFiles = await page.evaluate(() => {
      const links = Array.from(document.querySelectorAll('link[rel="stylesheet"]'));
      return links.map(link => ({
        href: link.href,
        loaded: link.sheet !== null
      }));
    });
    
    console.log('\n📋 CSS Files Status:');
    if (cssFiles.length === 0) {
      console.log('❌ No CSS files found!');
    } else {
      cssFiles.forEach(css => {
        console.log(`  ${css.loaded ? '✅' : '❌'} ${css.href}`);
      });
    }
    
    // Check computed styles on body
    const bodyStyles = await page.evaluate(() => {
      const body = document.body;
      const computed = window.getComputedStyle(body);
      return {
        fontFamily: computed.fontFamily,
        backgroundColor: computed.backgroundColor,
        color: computed.color,
        margin: computed.margin,
        padding: computed.padding
      };
    });
    
    console.log('\n📊 Body Computed Styles:');
    Object.entries(bodyStyles).forEach(([key, value]) => {
      console.log(`  ${key}: ${value}`);
    });
    
    // Check for MUI and Tailwind classes
    const classAnalysis = await page.evaluate(() => {
      const allElements = document.querySelectorAll('*');
      const muiClasses = [];
      const tailwindClasses = [];
      const customClasses = [];
      
      allElements.forEach(el => {
        const classes = Array.from(el.classList);
        classes.forEach(cls => {
          if (cls.startsWith('MuiBox-') || cls.startsWith('Mui')) {
            if (!muiClasses.includes(cls)) muiClasses.push(cls);
          } else if (cls.match(/^(bg-|text-|p-|m-|flex|grid|w-|h-)/)) {
            if (!tailwindClasses.includes(cls)) tailwindClasses.push(cls);
          } else if (cls && !cls.startsWith('css-')) {
            if (!customClasses.includes(cls)) customClasses.push(cls);
          }
        });
      });
      
      return { muiClasses, tailwindClasses, customClasses };
    });
    
    console.log('\n🎨 CSS Classes Analysis:');
    console.log(`  MUI Classes found: ${classAnalysis.muiClasses.length}`);
    if (classAnalysis.muiClasses.length > 0) {
      console.log(`    Examples: ${classAnalysis.muiClasses.slice(0, 5).join(', ')}`);
    }
    console.log(`  Tailwind Classes found: ${classAnalysis.tailwindClasses.length}`);
    if (classAnalysis.tailwindClasses.length > 0) {
      console.log(`    Examples: ${classAnalysis.tailwindClasses.slice(0, 5).join(', ')}`);
    }
    console.log(`  Custom Classes found: ${classAnalysis.customClasses.length}`);
    if (classAnalysis.customClasses.length > 0) {
      console.log(`    Examples: ${classAnalysis.customClasses.slice(0, 5).join(', ')}`);
    }
    
    // Test navigation to different routes
    const routes = [
      { path: '/dashboard', name: 'Dashboard' },
      { path: '/record', name: 'Record' },
      { path: '/upload', name: 'Upload' },
      { path: '/speeches', name: 'Speeches' }
    ];
    
    console.log('\n🔍 Testing navigation to different routes...\n');
    
    for (const route of routes) {
      console.log(`📍 Navigating to ${route.name} (${route.path})...`);
      
      try {
        await page.goto(`http://localhost:3000${route.path}`, {
          waitUntil: 'networkidle',
          timeout: 10000
        });
        
        await page.screenshot({ 
          path: `screenshots/${route.name.toLowerCase()}.png`,
          fullPage: true 
        });
        
        console.log(`✅ ${route.name} screenshot saved`);
        
        // Check for visible content
        const hasContent = await page.evaluate(() => {
          const main = document.querySelector('main, .MuiContainer-root, [role="main"]');
          return main && main.textContent.trim().length > 0;
        });
        
        console.log(`  Content visible: ${hasContent ? '✅' : '❌'}`);
        
      } catch (error) {
        console.log(`❌ Error navigating to ${route.name}: ${error.message}`);
      }
    }
    
    // Check for MUI theme
    console.log('\n🎨 Checking MUI Theme...');
    const muiTheme = await page.evaluate(() => {
      const themeProvider = document.querySelector('[class*="MuiThemeProvider"]');
      const cssBaseline = document.querySelector('[class*="MuiCssBaseline"]');
      return {
        hasThemeProvider: !!themeProvider,
        hasCssBaseline: !!cssBaseline
      };
    });
    
    console.log(`  MUI ThemeProvider: ${muiTheme.hasThemeProvider ? '✅' : '❌'}`);
    console.log(`  MUI CssBaseline: ${muiTheme.hasCssBaseline ? '✅' : '❌'}`);
    
    // Final visual assessment
    console.log('\n📝 Visual Assessment Summary:');
    console.log('================================');
    
    const assessment = await page.evaluate(() => {
      const issues = [];
      
      // Check if page looks unstyled
      const body = document.body;
      const bodyBg = window.getComputedStyle(body).backgroundColor;
      if (bodyBg === 'rgba(0, 0, 0, 0)' || bodyBg === 'rgb(255, 255, 255)') {
        issues.push('Page appears to have default/no background styling');
      }
      
      // Check for default font
      const bodyFont = window.getComputedStyle(body).fontFamily;
      if (bodyFont.includes('Times New Roman') || bodyFont === 'serif') {
        issues.push('Using default serif font - custom fonts not loading');
      }
      
      // Check for any styled elements
      const styledElements = document.querySelectorAll('[style], [class]');
      if (styledElements.length === 0) {
        issues.push('No styled elements found on page');
      }
      
      return issues;
    });
    
    if (assessment.length > 0) {
      console.log('🚨 Issues Found:');
      assessment.forEach(issue => console.log(`  - ${issue}`));
    } else {
      console.log('✅ No obvious styling issues detected');
    }
    
  } catch (error) {
    console.error('❌ Test failed:', error);
  } finally {
    await browser.close();
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