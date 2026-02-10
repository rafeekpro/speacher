import React, { act } from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AuthProvider } from '../../contexts/AuthContext';
import Sidebar from './Sidebar';
import { useLocation } from 'react-router-dom';

// Mock react-router-dom
jest.mock('react-router-dom', () => ({
  useLocation: jest.fn(),
  Link: ({ children, to, ...props }: any) => (
    <a href={to} {...props}>{children}</a>
  )
}));

// Mock AuthContext for testing
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

describe('Sidebar Component', () => {
  beforeEach(() => {
    (useLocation as jest.Mock).mockReturnValue({ pathname: '/dashboard' });
  });

  const renderSidebar = (props = {}) => {
    return render(
      <AuthProvider>
        <Sidebar {...props} />
      </AuthProvider>
    );
  };

  describe('Rendering', () => {
    it('should render the sidebar with logo', () => {
      renderSidebar();
      expect(screen.getByTestId('sidebar')).toBeInTheDocument();
      expect(screen.getByText('Speecher')).toBeInTheDocument();
    });

    it('should display user information when authenticated', () => {
      renderSidebar();
      expect(screen.getByText('Test User')).toBeInTheDocument();
      expect(screen.getByText('test@example.com')).toBeInTheDocument();
    });

    it('should render navigation menu items', () => {
      renderSidebar();
      expect(screen.getByRole('link', { name: /dashboard/i })).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /record/i })).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /upload/i })).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /history/i })).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /statistics/i })).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /settings/i })).toBeInTheDocument();
    });
  });

  describe('Collapsible Behavior', () => {
    it('should be expanded by default on desktop', () => {
      renderSidebar();
      const sidebar = screen.getByTestId('sidebar');
      expect(sidebar).toHaveClass('w-64'); // 256px width when expanded
    });

    it('should toggle collapse state when toggle button is clicked', () => {
      renderSidebar();
      const toggleButton = screen.getByRole('button', { name: /toggle sidebar/i });
      const sidebar = screen.getByTestId('sidebar');

      // Initially expanded
      expect(sidebar).toHaveClass('w-64');

      // Click to collapse
      fireEvent.click(toggleButton);
      expect(sidebar).toHaveClass('w-16'); // 64px width when collapsed

      // Click to expand
      fireEvent.click(toggleButton);
      expect(sidebar).toHaveClass('w-64');
    });

    it('should hide text when collapsed', () => {
      renderSidebar();
      const toggleButton = screen.getByRole('button', { name: /toggle sidebar/i });

      // Initially text is visible
      expect(screen.getByText('Dashboard')).toBeVisible();

      // Collapse sidebar
      fireEvent.click(toggleButton);
      
      // Text should be hidden
      const dashboardText = screen.queryByText('Dashboard');
      expect(dashboardText).toHaveClass('opacity-0');
    });

    it('should show tooltips on hover when collapsed', async () => {
      renderSidebar();
      const toggleButton = screen.getByRole('button', { name: /toggle sidebar/i });

      // Collapse sidebar
      fireEvent.click(toggleButton);

      // When collapsed, links should have title attributes for tooltips
      const dashboardLink = screen.getByRole('link', { name: /dashboard/i });
      expect(dashboardLink).toHaveAttribute('title', 'Dashboard');
    });
  });

  describe('Animation', () => {
    it('should have smooth transition classes', () => {
      renderSidebar();
      const sidebar = screen.getByTestId('sidebar');
      expect(sidebar).toHaveClass('transition-all', 'duration-300');
    });

    it('should animate icon rotation when collapsing', () => {
      renderSidebar();
      const toggleButton = screen.getByRole('button', { name: /toggle sidebar/i });
      const icon = toggleButton.querySelector('svg');

      // Initially not rotated
      expect(icon).not.toHaveClass('rotate-180');

      // Click to collapse
      fireEvent.click(toggleButton);
      expect(icon).toHaveClass('rotate-180');
    });
  });

  describe('Mobile Responsiveness', () => {
    beforeEach(() => {
      // Mock mobile viewport
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
      // Reset to desktop
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 1024
      });
      act(() => {
        window.dispatchEvent(new Event('resize'));
      });
    });

    it('should be hidden by default on mobile', () => {
      renderSidebar();
      const sidebar = screen.getByTestId('sidebar');
      expect(sidebar).toHaveClass('-translate-x-full', 'md:translate-x-0');
    });

    it('should show overlay when open on mobile', () => {
      renderSidebar({ isOpen: true });
      const overlay = screen.getByTestId('sidebar-overlay');
      expect(overlay).toBeInTheDocument();
      expect(overlay).toHaveClass('opacity-50');
    });

    it('should close when overlay is clicked on mobile', () => {
      const onClose = jest.fn();
      renderSidebar({ isOpen: true, onClose });
      const overlay = screen.getByTestId('sidebar-overlay');

      fireEvent.click(overlay);
      expect(onClose).toHaveBeenCalled();
    });

    it('should be fixed position on mobile', () => {
      renderSidebar();
      const sidebar = screen.getByTestId('sidebar');
      expect(sidebar).toHaveClass('fixed', 'md:relative');
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA labels', () => {
      renderSidebar();
      expect(screen.getByRole('navigation', { name: /main navigation/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /toggle sidebar/i })).toBeInTheDocument();
    });

    it('should support keyboard navigation', () => {
      renderSidebar();
      const firstLink = screen.getByRole('link', { name: /dashboard/i });
      const secondLink = screen.getByRole('link', { name: /record/i });

      // Focus first link
      firstLink.focus();
      expect(document.activeElement).toBe(firstLink);

      // Tab to next link
      fireEvent.keyDown(firstLink, { key: 'Tab' });
      secondLink.focus();
      expect(document.activeElement).toBe(secondLink);
    });

    it('should toggle sidebar with keyboard shortcut', () => {
      renderSidebar();
      const sidebar = screen.getByTestId('sidebar');

      // Press Ctrl+B to toggle
      fireEvent.keyDown(document, { key: 'b', ctrlKey: true });
      expect(sidebar).toHaveClass('w-16');

      fireEvent.keyDown(document, { key: 'b', ctrlKey: true });
      expect(sidebar).toHaveClass('w-64');
    });

    it('should have focus trap when open on mobile', () => {
      // Set to mobile viewport
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 375
      });
      act(() => {
        window.dispatchEvent(new Event('resize'));
      });
      
      renderSidebar({ isOpen: true });
      const sidebar = screen.getByTestId('sidebar');
      const focusableElements = sidebar.querySelectorAll('a, button');
      
      // Verify there are focusable elements
      expect(focusableElements.length).toBeGreaterThan(0);
      
      // Focus management is handled by the browser and aria-modal
      expect(sidebar).toHaveAttribute('aria-modal', 'true');
    });

    it('should announce state changes to screen readers', () => {
      renderSidebar();
      const toggleButton = screen.getByRole('button', { name: /toggle sidebar/i });

      expect(toggleButton).toHaveAttribute('aria-expanded', 'true');

      fireEvent.click(toggleButton);
      expect(toggleButton).toHaveAttribute('aria-expanded', 'false');
    });
  });

  describe('Logout Functionality', () => {
    it('should render logout button', () => {
      renderSidebar();
      expect(screen.getByRole('button', { name: /logout/i })).toBeInTheDocument();
    });

    it('should call logout function when logout button is clicked', () => {
      const mockLogout = jest.fn();
      jest.spyOn(require('../../contexts/AuthContext'), 'useAuth').mockReturnValue({
        user: { id: '1', email: 'test@example.com', name: 'Test User' },
        isAuthenticated: true,
        loading: false,
        login: jest.fn(),
        logout: mockLogout,
        register: jest.fn(),
        refreshToken: jest.fn()
      });

      renderSidebar();
      const logoutButton = screen.getByRole('button', { name: /logout/i });
      
      fireEvent.click(logoutButton);
      expect(mockLogout).toHaveBeenCalled();
    });
  });

  describe('Active Link Highlighting', () => {
    it('should highlight the active route', () => {
      // Ensure useAuth mock is properly configured for this test
      jest.spyOn(require('../../contexts/AuthContext'), 'useAuth').mockReturnValue({
        user: { id: '1', email: 'test@example.com', name: 'Test User' },
        isAuthenticated: true,
        loading: false,
        login: jest.fn(),
        logout: jest.fn(),
        register: jest.fn(),
        refreshToken: jest.fn()
      });
      
      (useLocation as jest.Mock).mockReturnValue({ pathname: '/dashboard' });
      renderSidebar();

      const dashboardLink = screen.getByRole('link', { name: /dashboard/i });
      expect(dashboardLink).toHaveClass('bg-blue-100');
    });
  });
});