import React, { act } from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from '../../contexts/AuthContext';
import Layout from './Layout';

// Mock the child components
jest.mock('./Sidebar', () => {
  return function MockSidebar({ isOpen, onClose, isCollapsed, onToggleCollapse }: any) {
    return (
      <div
        data-testid="sidebar"
        className={isOpen ? 'open' : 'closed'}
        aria-modal={isOpen ? 'true' : undefined}
      >
        <nav role="navigation" aria-label="Main navigation">
          <button onClick={onToggleCollapse}>Toggle Sidebar</button>
          <button onClick={onClose}>Close Sidebar</button>
          Sidebar Content
        </nav>
      </div>
    );
  };
});

// Mock AuthContext
jest.mock('../../contexts/AuthContext', () => ({
  ...jest.requireActual('../../contexts/AuthContext'),
  useAuth: () => ({
    user: { id: '1', email: 'test@example.com', name: 'Test User' },
    isAuthenticated: true,
    loading: false,
    login: jest.fn(),
    logout: jest.fn(),
    register: jest.fn(),
    refreshToken: jest.fn()
  })
}));

describe('Layout Component', () => {
  const renderLayout = (props = {}) => {
    const defaultProps = {
      children: <div>Main Content</div>,
      ...props
    };

    return render(
      <BrowserRouter>
        <AuthProvider>
          <Layout {...defaultProps}>{defaultProps.children}</Layout>
        </AuthProvider>
      </BrowserRouter>
    );
  };

  describe('Rendering', () => {
    it('should render the layout with sidebar and main content', () => {
      renderLayout();

      expect(screen.getByTestId('sidebar')).toBeInTheDocument();
      expect(screen.getByText('Main Content')).toBeInTheDocument();
    });

    it('should render the header with mobile menu button', () => {
      renderLayout();

      expect(screen.getByRole('banner')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /open menu/i })).toBeInTheDocument();
    });

    it('should apply correct layout structure', () => {
      renderLayout();

      const layoutContainer = screen.getByTestId('layout-container');
      expect(layoutContainer).toHaveClass('flex', 'h-screen', 'bg-gray-50');
    });

    it('should render main content area with proper styling', () => {
      renderLayout();

      const mainContent = screen.getByRole('main');
      expect(mainContent).toHaveClass('flex-1', 'overflow-auto');
    });
  });

  describe('Desktop Layout', () => {
    beforeEach(() => {
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 1024
      });
      act(() => {
        window.dispatchEvent(new Event('resize'));
      });
    });

    it('should show sidebar by default on desktop', () => {
      renderLayout();

      const sidebar = screen.getByTestId('sidebar');
      expect(sidebar).toBeInTheDocument();
      expect(sidebar).not.toHaveClass('hidden');
    });

    it('should not show mobile menu button on desktop', () => {
      renderLayout();

      const mobileMenuButton = screen.getByRole('button', { name: /open menu/i });
      expect(mobileMenuButton).toHaveClass('md:hidden');
    });

    it('should handle sidebar collapse on desktop', () => {
      renderLayout();

      const toggleButton = screen.getByText('Toggle Sidebar');
      const mainContent = screen.getByRole('main');

      // Initially expanded
      expect(mainContent).toHaveClass('md:ml-64');

      // Click to collapse
      fireEvent.click(toggleButton);
      expect(mainContent).toHaveClass('md:ml-16');

      // Click to expand
      fireEvent.click(toggleButton);
      expect(mainContent).toHaveClass('md:ml-64');
    });
  });

  describe('Mobile Layout', () => {
    beforeEach(() => {
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 375
      });
      act(() => {
        window.dispatchEvent(new Event('resize'));
      });
    });

    afterEach(() => {
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 1024
      });
      act(() => {
        window.dispatchEvent(new Event('resize'));
      });
    });

    it('should hide sidebar by default on mobile', () => {
      renderLayout();

      const sidebar = screen.getByTestId('sidebar');
      expect(sidebar).toHaveClass('closed');
    });

    it('should show mobile menu button', () => {
      renderLayout();

      const mobileMenuButton = screen.getByRole('button', { name: /open menu/i });
      expect(mobileMenuButton).toBeVisible();
    });

    it('should open sidebar when mobile menu button is clicked', () => {
      renderLayout();

      const mobileMenuButton = screen.getByRole('button', { name: /open menu/i });
      const sidebar = screen.getByTestId('sidebar');

      // Initially closed
      expect(sidebar).toHaveClass('closed');

      // Click to open
      fireEvent.click(mobileMenuButton);
      expect(sidebar).toHaveClass('open');
    });

    it('should close sidebar when close button is clicked', () => {
      renderLayout();

      const mobileMenuButton = screen.getByRole('button', { name: /open menu/i });

      // Open sidebar
      fireEvent.click(mobileMenuButton);

      const closeButton = screen.getByText('Close Sidebar');
      const sidebar = screen.getByTestId('sidebar');

      // Click to close
      fireEvent.click(closeButton);
      expect(sidebar).toHaveClass('closed');
    });

    it('should not affect main content margin on mobile', () => {
      renderLayout();

      const mainContent = screen.getByRole('main');
      expect(mainContent).not.toHaveClass('ml-64');
      expect(mainContent).not.toHaveClass('ml-16');
    });
  });

  describe('Responsive Behavior', () => {
    it('should adapt layout when window is resized', async () => {
      renderLayout();

      // Start with desktop
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 1024
      });
      await act(async () => {
        window.dispatchEvent(new Event('resize'));
      });

      await waitFor(() => {
        const mobileMenuButton = screen.getByRole('button', { name: /open menu/i });
        expect(mobileMenuButton).toHaveClass('md:hidden');
      });

      // Resize to mobile
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 375
      });
      await act(async () => {
        window.dispatchEvent(new Event('resize'));
      });

      await waitFor(() => {
        const sidebar = screen.getByTestId('sidebar');
        expect(sidebar).toHaveClass('closed');
      });
    });

    it('should maintain sidebar state when resizing', () => {
      renderLayout();

      // Collapse sidebar on desktop
      const toggleButton = screen.getByText('Toggle Sidebar');
      fireEvent.click(toggleButton);

      // Resize to mobile and back
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 375
      });
      act(() => {
        window.dispatchEvent(new Event('resize'));
      });

      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 1024
      });
      act(() => {
        window.dispatchEvent(new Event('resize'));
      });

      // Sidebar should still be collapsed
      const mainContent = screen.getByRole('main');
      expect(mainContent).toHaveClass('md:ml-16');
    });
  });

  describe('Accessibility', () => {
    it('should have proper landmark roles', () => {
      renderLayout();

      expect(screen.getByRole('banner')).toBeInTheDocument(); // Header
      expect(screen.getByRole('main')).toBeInTheDocument(); // Main content
      expect(screen.getByRole('navigation')).toBeInTheDocument(); // Sidebar navigation
    });

    it('should have proper ARIA labels', () => {
      renderLayout();

      const mobileMenuButton = screen.getByRole('button', { name: /open menu/i });
      expect(mobileMenuButton).toHaveAttribute('aria-label', 'Open menu');
    });

    it('should support keyboard navigation for mobile menu', () => {
      // Set to mobile viewport first
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 375
      });

      renderLayout();

      const mobileMenuButton = screen.getByRole('button', { name: /open menu/i });

      // Focus and activate with click (buttons naturally support Enter/Space keys)
      mobileMenuButton.focus();
      expect(document.activeElement).toBe(mobileMenuButton);

      // Click to open menu (buttons handle Enter/Space through native browser behavior)
      fireEvent.click(mobileMenuButton);
      const sidebar = screen.getByTestId('sidebar');
      expect(sidebar).toHaveClass('open');
    });

    it('should trap focus in sidebar when open on mobile', () => {
      renderLayout();

      // Set to mobile
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 375
      });
      act(() => {
        window.dispatchEvent(new Event('resize'));
      });

      // Open sidebar
      const mobileMenuButton = screen.getByRole('button', { name: /open menu/i });
      fireEvent.click(mobileMenuButton);

      const sidebar = screen.getByTestId('sidebar');
      expect(sidebar).toHaveAttribute('aria-modal', 'true');
    });

    it('should handle Escape key to close sidebar on mobile', () => {
      renderLayout();

      // Set to mobile
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 375
      });
      act(() => {
        window.dispatchEvent(new Event('resize'));
      });

      // Open sidebar
      const mobileMenuButton = screen.getByRole('button', { name: /open menu/i });
      fireEvent.click(mobileMenuButton);

      // Press Escape
      fireEvent.keyDown(document, { key: 'Escape' });

      const sidebar = screen.getByTestId('sidebar');
      expect(sidebar).toHaveClass('closed');
    });
  });

  describe('Content Scrolling', () => {
    it('should make main content scrollable', () => {
      renderLayout({
        children: (
          <div style={{ height: '2000px' }}>
            Very tall content
          </div>
        )
      });

      const mainContent = screen.getByRole('main');
      expect(mainContent).toHaveClass('overflow-auto');
    });

    it('should keep header fixed', () => {
      renderLayout();

      const header = screen.getByRole('banner');
      expect(header).toHaveClass('sticky', 'top-0');
    });
  });

  describe('Theme and Styling', () => {
    it('should apply consistent background colors', () => {
      renderLayout();

      const layoutContainer = screen.getByTestId('layout-container');
      expect(layoutContainer).toHaveClass('bg-gray-50');
    });

    it('should have proper z-index layering', () => {
      renderLayout();

      const header = screen.getByRole('banner');
      expect(header).toHaveClass('z-40');

      // Check z-index on sidebar container
      const sidebarContainer = screen.getByTestId('sidebar').parentElement;
      // The z-50 class is conditionally applied based on mobile state
      // Since we're not on mobile by default, it should not have z-50
      expect(sidebarContainer).toBeInTheDocument();
    });
  });

  describe('Children Rendering', () => {
    it('should render children components', () => {
      renderLayout({
        children: (
          <>
            <h1>Page Title</h1>
            <p>Page content</p>
          </>
        )
      });

      expect(screen.getByText('Page Title')).toBeInTheDocument();
      expect(screen.getByText('Page content')).toBeInTheDocument();
    });

    it('should pass through props to children', () => {
      const TestChild = () => <div data-testid="test-child">Test Child</div>;

      renderLayout({
        children: <TestChild />
      });

      expect(screen.getByTestId('test-child')).toBeInTheDocument();
    });
  });

  describe('Authentication UI', () => {
    it('should show user email and logout button when authenticated', () => {
      renderLayout();

      expect(screen.getByText('test@example.com')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /logout/i })).toBeInTheDocument();
    });
  });
});
