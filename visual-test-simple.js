const http = require('http');
const fs = require('fs');
const path = require('path');

// Simple visual test by fetching the HTML and analyzing it
async function analyzeStyles() {
  console.log('🔍 Visual Test of Speecher Application\n');
  console.log('========================================\n');
  
  // Fetch the homepage
  const getPage = (url) => {
    return new Promise((resolve, reject) => {
      http.get(url, (res) => {
        let data = '';
        res.on('data', chunk => data += chunk);
        res.on('end', () => resolve(data));
      }).on('error', reject);
    });
  };
  
  try {
    console.log('📍 Fetching http://localhost:3000...\n');
    const html = await getPage('http://localhost:3000');
    
    // Basic analysis
    console.log('📊 HTML Analysis:');
    console.log(`  Total HTML size: ${html.length} characters`);
    
    // Check for CSS links
    const cssLinks = html.match(/<link[^>]*rel=["']stylesheet["'][^>]*>/gi) || [];
    console.log(`\n🎨 CSS Files: ${cssLinks.length} found`);
    cssLinks.forEach(link => {
      const href = link.match(/href=["']([^"']+)["']/i);
      if (href) {
        console.log(`  - ${href[1]}`);
      }
    });
    
    // Check for inline styles
    const inlineStyles = html.match(/<style[^>]*>[\s\S]*?<\/style>/gi) || [];
    console.log(`\n💅 Inline <style> tags: ${inlineStyles.length} found`);
    
    // Check for script tags
    const scriptTags = html.match(/<script[^>]*>/gi) || [];
    console.log(`\n📜 Script tags: ${scriptTags.length} found`);
    
    // Check for React root
    const hasReactRoot = html.includes('id="root"');
    console.log(`\n⚛️ React root element: ${hasReactRoot ? '✅ Found' : '❌ Not found'}`);
    
    // Check for class attributes
    const classMatches = html.match(/class=["'][^"']+["']/gi) || [];
    const classNames = new Set();
    classMatches.forEach(match => {
      const classes = match.match(/class=["']([^"']+)["']/i);
      if (classes) {
        classes[1].split(' ').forEach(cls => classNames.add(cls));
      }
    });
    
    console.log(`\n🏷️ CSS Classes Analysis:`);
    console.log(`  Total unique classes: ${classNames.size}`);
    
    // Categorize classes
    const muiClasses = Array.from(classNames).filter(cls => cls.startsWith('Mui') || cls.startsWith('MuiBox'));
    const tailwindClasses = Array.from(classNames).filter(cls => 
      cls.match(/^(bg-|text-|p-|m-|flex|grid|w-|h-|border|rounded)/));
    const cssModules = Array.from(classNames).filter(cls => cls.startsWith('css-'));
    
    console.log(`  MUI classes: ${muiClasses.length}`);
    if (muiClasses.length > 0) {
      console.log(`    Examples: ${muiClasses.slice(0, 5).join(', ')}`);
    }
    
    console.log(`  Tailwind classes: ${tailwindClasses.length}`);
    if (tailwindClasses.length > 0) {
      console.log(`    Examples: ${tailwindClasses.slice(0, 5).join(', ')}`);
    }
    
    console.log(`  CSS Modules: ${cssModules.length}`);
    if (cssModules.length > 0) {
      console.log(`    Examples: ${cssModules.slice(0, 5).join(', ')}`);
    }
    
    // Check for common issues
    console.log('\n🚨 Common Issues Check:');
    const issues = [];
    
    if (cssLinks.length === 0 && inlineStyles.length === 0) {
      issues.push('❌ No CSS files or inline styles found - page will be completely unstyled');
    }
    
    if (!hasReactRoot) {
      issues.push('❌ React root element not found - React app may not be mounting');
    }
    
    if (html.includes('Error') || html.includes('error')) {
      issues.push('⚠️ Error text detected in HTML');
    }
    
    if (html.includes('Cannot GET') || html.includes('404')) {
      issues.push('❌ 404 or routing error detected');
    }
    
    if (classNames.size === 0) {
      issues.push('❌ No CSS classes found - indicates no styling applied');
    }
    
    if (muiClasses.length === 0 && tailwindClasses.length === 0) {
      issues.push('⚠️ No MUI or Tailwind classes detected - framework CSS may not be loading');
    }
    
    if (issues.length > 0) {
      issues.forEach(issue => console.log(`  ${issue}`));
    } else {
      console.log('  ✅ No obvious issues detected');
    }
    
    // Save HTML for inspection
    fs.writeFileSync('homepage-output.html', html);
    console.log('\n📁 Full HTML saved to homepage-output.html for inspection');
    
    // Check if it's a development build error page
    if (html.includes('Failed to compile') || html.includes('Compiled with problems')) {
      console.log('\n🔴 CRITICAL: React development server showing compilation errors!');
      console.log('The app is not running due to build errors.');
      
      // Extract error messages
      const errorMatch = html.match(/<pre[^>]*>([\s\S]*?)<\/pre>/gi);
      if (errorMatch) {
        console.log('\nCompilation errors found:');
        errorMatch.forEach(error => {
          const cleaned = error.replace(/<[^>]*>/g, '').trim();
          console.log(cleaned);
        });
      }
    }
    
  } catch (error) {
    console.error('❌ Failed to fetch page:', error.message);
    console.log('\nPossible reasons:');
    console.log('  1. Development server not running on port 3000');
    console.log('  2. Application crashed during startup');
    console.log('  3. Network/firewall blocking connection');
  }
}

// Run the test
analyzeStyles().catch(console.error);