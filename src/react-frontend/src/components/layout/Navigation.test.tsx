import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { act } from 'react';
import Navigation from './Navigation';
import { useLocation } from 'react-router-dom';

// Mock react-router-dom
jest.mock('react-router-dom', () => ({
  useLocation: jest.fn(),
  Link: ({ children, to, ...props }: any) => (
    <a href={to} {...props}>{children}</a>
  )
}));

describe('Navigation Component', () => {
  const defaultNavItems = [
    { path: '/dashboard', label: 'Dashboard', icon: 'dashboard' },
    { path: '/record', label: 'Record', icon: 'mic' },
    { path: '/upload', label: 'Upload', icon: 'upload' },
    { path: '/history', label: 'History', icon: 'history' },
    { path: '/statistics', label: 'Statistics', icon: 'chart' },
    { path: '/settings', label: 'Settings', icon: 'settings' }
  ];

  const renderNavigation = (props = {}) => {
    const defaultProps = {
      items: defaultNavItems,
      isCollapsed: false,
      ...props
    };

    return render(
      <Navigation {...defaultProps} />
    );
  };

  beforeEach(() => {
    (useLocation as jest.Mock).mockReturnValue({ pathname: '/dashboard' });
  });

  describe('Rendering', () => {
    it('should render all navigation items', () => {
      renderNavigation();
      
      defaultNavItems.forEach(item => {
        expect(screen.getByRole('link', { name: new RegExp(item.label, 'i') })).toBeInTheDocument();
      });
    });

    it('should render icons for each navigation item', () => {
      renderNavigation();
      
      defaultNavItems.forEach(item => {
        const link = screen.getByRole('link', { name: new RegExp(item.label, 'i') });
        const icon = link.querySelector('[data-testid="nav-icon"]');
        expect(icon).toBeInTheDocument();
      });
    });

    it('should show labels when not collapsed', () => {
      renderNavigation({ isCollapsed: false });
      
      defaultNavItems.forEach(item => {
        expect(screen.getByText(item.label)).toBeVisible();
      });
    });

    it('should hide labels when collapsed', () => {
      renderNavigation({ isCollapsed: true });
      
      defaultNavItems.forEach(item => {
        const label = screen.getByText(item.label);
        expect(label).toHaveClass('opacity-0');
      });
    });
  });

  describe('Active State', () => {
    it('should highlight the active navigation item', () => {
      (useLocation as jest.Mock).mockReturnValue({ pathname: '/record' });
      renderNavigation();
      
      const recordLink = screen.getByRole('link', { name: /record/i });
      expect(recordLink).toHaveClass('bg-blue-100', 'text-blue-700');
    });

    it('should not highlight inactive navigation items', () => {
      (useLocation as jest.Mock).mockReturnValue({ pathname: '/record' });
      renderNavigation();
      
      const dashboardLink = screen.getByRole('link', { name: /dashboard/i });
      expect(dashboardLink).not.toHaveClass('bg-blue-100');
    });

    it('should update active state when location changes', () => {
      const { rerender } = renderNavigation();
      
      // Initially on dashboard
      let dashboardLink = screen.getByRole('link', { name: /dashboard/i });
      expect(dashboardLink).toHaveClass('bg-blue-100');
      
      // Change to record
      (useLocation as jest.Mock).mockReturnValue({ pathname: '/record' });
      rerender(
        <Navigation items={defaultNavItems} isCollapsed={false} />
      );
      
      const recordLink = screen.getByRole('link', { name: /record/i });
      dashboardLink = screen.getByRole('link', { name: /dashboard/i });
      expect(recordLink).toHaveClass('bg-blue-100');
      expect(dashboardLink).not.toHaveClass('bg-blue-100');
    });
  });

  describe('Collapsed State', () => {
    it('should apply correct styling when collapsed', () => {
      renderNavigation({ isCollapsed: true });
      
      const navContainer = screen.getByRole('navigation');
      expect(navContainer).toHaveClass('space-y-1');
      
      const links = screen.getAllByRole('link');
      links.forEach(link => {
        expect(link).toHaveClass('justify-center');
      });
    });

    it('should apply correct styling when expanded', () => {
      renderNavigation({ isCollapsed: false });
      
      const links = screen.getAllByRole('link');
      links.forEach(link => {
        expect(link).toHaveClass('justify-start');
      });
    });

    it('should show tooltips when collapsed', () => {
      renderNavigation({ isCollapsed: true });
      
      defaultNavItems.forEach(item => {
        const link = screen.getByRole('link', { name: new RegExp(item.label, 'i') });
        expect(link).toHaveAttribute('title', item.label);
      });
    });

    it('should not show tooltips when expanded', () => {
      renderNavigation({ isCollapsed: false });
      
      defaultNavItems.forEach(item => {
        const link = screen.getByRole('link', { name: new RegExp(item.label, 'i') });
        expect(link).not.toHaveAttribute('title');
      });
    });
  });

  describe('Accessibility', () => {
    it('should have proper navigation role', () => {
      renderNavigation();
      expect(screen.getByRole('navigation')).toBeInTheDocument();
    });

    it('should have proper link roles', () => {
      renderNavigation();
      const links = screen.getAllByRole('link');
      expect(links).toHaveLength(defaultNavItems.length);
    });

    it('should have aria-current for active link', () => {
      (useLocation as jest.Mock).mockReturnValue({ pathname: '/dashboard' });
      renderNavigation();
      
      const dashboardLink = screen.getByRole('link', { name: /dashboard/i });
      expect(dashboardLink).toHaveAttribute('aria-current', 'page');
    });

    it('should support keyboard navigation', () => {
      renderNavigation();
      
      const links = screen.getAllByRole('link');
      
      // Focus first link
      links[0].focus();
      expect(document.activeElement).toBe(links[0]);
      
      // Tab to next link
      fireEvent.keyDown(links[0], { key: 'Tab' });
      links[1].focus();
      expect(document.activeElement).toBe(links[1]);
    });

    it('should have descriptive aria-labels for icons when collapsed', () => {
      renderNavigation({ isCollapsed: true });
      
      defaultNavItems.forEach(item => {
        const link = screen.getByRole('link', { name: new RegExp(item.label, 'i') });
        expect(link).toHaveAttribute('aria-label', item.label);
      });
    });
  });

  describe('Hover Effects', () => {
    it('should apply hover styles', () => {
      renderNavigation();
      
      const dashboardLink = screen.getByRole('link', { name: /dashboard/i });
      expect(dashboardLink).toHaveClass('hover:bg-gray-100');
    });

    it('should show transition effects', () => {
      renderNavigation();
      
      const links = screen.getAllByRole('link');
      links.forEach(link => {
        expect(link).toHaveClass('transition-all', 'duration-200');
      });
    });
  });

  describe('Custom Navigation Items', () => {
    it('should render custom navigation items', () => {
      const customItems = [
        { path: '/custom1', label: 'Custom 1', icon: 'star' },
        { path: '/custom2', label: 'Custom 2', icon: 'heart' }
      ];
      
      renderNavigation({ items: customItems });
      
      expect(screen.getByRole('link', { name: /custom 1/i })).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /custom 2/i })).toBeInTheDocument();
    });

    it('should handle empty navigation items', () => {
      renderNavigation({ items: [] });
      
      const navigation = screen.getByRole('navigation');
      expect(navigation).toBeInTheDocument();
      expect(screen.queryAllByRole('link')).toHaveLength(0);
    });
  });

  describe('Icon Rendering', () => {
    it('should render appropriate icons for each item', () => {
      renderNavigation();
      
      const dashboardLink = screen.getByRole('link', { name: /dashboard/i });
      const icon = dashboardLink.querySelector('[data-testid="nav-icon"]');
      expect(icon).toHaveAttribute('data-icon', 'dashboard');
    });

    it('should scale icons when collapsed', () => {
      renderNavigation({ isCollapsed: true });
      
      const links = screen.getAllByRole('link');
      links.forEach(link => {
        const icon = link.querySelector('[data-testid="nav-icon"]');
        expect(icon).toHaveClass('w-6', 'h-6');
      });
    });

    it('should use normal size icons when expanded', () => {
      renderNavigation({ isCollapsed: false });
      
      const links = screen.getAllByRole('link');
      links.forEach(link => {
        const icon = link.querySelector('[data-testid="nav-icon"]');
        expect(icon).toHaveClass('w-5', 'h-5');
      });
    });
  });
});