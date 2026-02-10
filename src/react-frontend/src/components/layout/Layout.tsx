import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Sidebar from './Sidebar';
import { useAuth } from '../../contexts/AuthContext';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const { user, isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  // Helper function to get main content margin class
  const getMainMarginClass = () => {
    if (isMobile) return '';
    return isSidebarCollapsed ? 'md:ml-16' : 'md:ml-64';
  };

  // Check if on mobile
  useEffect(() => {
    const checkMobile = () => {
      const mobile = window.innerWidth < 768;
      setIsMobile(mobile);
      // Close sidebar when switching to mobile
      if (mobile) {
        setIsSidebarOpen(false);
      }
    };

    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // Handle Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isMobile && isSidebarOpen) {
        setIsSidebarOpen(false);
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isMobile, isSidebarOpen]);

  const handleToggleSidebar = () => {
    if (isMobile) {
      setIsSidebarOpen(!isSidebarOpen);
    } else {
      setIsSidebarCollapsed(!isSidebarCollapsed);
    }
  };

  const handleCloseSidebar = () => {
    setIsSidebarOpen(false);
  };

  const handleToggleCollapse = () => {
    setIsSidebarCollapsed(!isSidebarCollapsed);
  };

  // Don't show sidebar and header for login/register pages
  if (!isAuthenticated) {
    return (
      <div data-testid="layout-container" className="min-h-screen bg-gray-50">
        {/* Simple centered header for auth pages */}
        <header
          role="banner"
          className="bg-white shadow-sm border-b border-gray-200"
        >
          <div className="flex items-center justify-center px-4 py-3">
            <h1 className="text-xl font-semibold text-gray-800">
              Speecher
            </h1>
          </div>
        </header>

        {/* Main Content */}
        <main
          role="main"
          className="flex items-center justify-center min-h-[calc(100vh-64px)] p-6"
        >
          <div className="w-full max-w-md">
            {children}
          </div>
        </main>
      </div>
    );
  }

  return (
    <div data-testid="layout-container" className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <div className={`${isMobile ? '' : 'z-50'}`}>
        <Sidebar
          isOpen={isSidebarOpen}
          onClose={handleCloseSidebar}
          isCollapsed={isSidebarCollapsed}
          onToggleCollapse={handleToggleCollapse}
        />
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <header
          role="banner"
          className="sticky top-0 z-40 bg-white shadow-sm border-b border-gray-200"
        >
          <div className="flex items-center justify-between px-4 py-3">
            {/* Mobile Menu Button */}
            <button
              type="button"
              onClick={handleToggleSidebar}
              className="md:hidden p-2 rounded-lg hover:bg-gray-100 transition-colors"
              aria-label="Open menu"
            >
              <svg
                className="w-6 h-6 text-gray-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 6h16M4 12h16M4 18h16"
                />
              </svg>
            </button>

            {/* Header Content */}
            <div className="flex-1 flex items-center justify-between">
              <h1 className="text-xl font-semibold text-gray-800 ml-4 md:ml-0">
                Speecher
              </h1>

              {/* User Info and Logout */}
              <div className="flex items-center space-x-4">
                <span className="text-sm text-gray-600 hidden sm:block">
                  {user?.email}
                </span>
                <button
                  type="button"
                  onClick={async () => {
                    await logout();
                    navigate('/login');
                  }}
                  className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
                >
                  Logout
                </button>
              </div>
            </div>
          </div>
        </header>

        {/* Main Content */}
        <main
          role="main"
          className={`
            flex-1 overflow-auto p-6
            transition-all duration-300
            ${getMainMarginClass()}
          `}
        >
          {children}
        </main>
      </div>
    </div>
  );
};

export default Layout;
