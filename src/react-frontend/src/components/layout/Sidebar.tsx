import React, { useEffect, useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import Navigation from './Navigation';

interface SidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({
  isOpen = false,
  onClose,
  isCollapsed: externalIsCollapsed,
  onToggleCollapse: externalOnToggleCollapse
}) => {
  const { user, logout } = useAuth();
  const [internalIsCollapsed, setInternalIsCollapsed] = useState(false);
  
  // Use external state if provided, otherwise use internal state
  const isCollapsed = externalIsCollapsed !== undefined ? externalIsCollapsed : internalIsCollapsed;
  const handleToggleCollapse = useMemo(
    () => externalOnToggleCollapse || (() => setInternalIsCollapsed(!internalIsCollapsed)),
    [externalOnToggleCollapse, internalIsCollapsed]
  );

  // Keyboard shortcut for toggling sidebar
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key === 'b') {
        e.preventDefault();
        handleToggleCollapse();
      }
      if (e.key === 'Escape' && isOpen && onClose) {
        onClose();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleToggleCollapse, isOpen, onClose]);

  // Navigation items
  const navItems = [
    { path: '/dashboard', label: 'Dashboard', icon: 'dashboard' },
    { path: '/record', label: 'Record', icon: 'mic' },
    { path: '/upload', label: 'Upload', icon: 'upload' },
    { path: '/history', label: 'History', icon: 'history' },
    { path: '/files', label: 'Files', icon: 'file' },
    { path: '/statistics', label: 'Statistics', icon: 'chart' },
    { path: '/settings', label: 'Settings', icon: 'settings' }
  ];

  // Check if on mobile
  const isMobile = typeof window !== 'undefined' && window.innerWidth < 768;

  return (
    <>
      {/* Overlay for mobile */}
      {isOpen && isMobile && (
        <div
          data-testid="sidebar-overlay"
          className="fixed inset-0 bg-black opacity-50 z-40 md:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <div
        data-testid="sidebar"
        className={`
          ${isCollapsed ? 'w-16' : 'w-64'}
          h-full bg-white shadow-lg transition-all duration-300 flex flex-col
          fixed md:relative z-50
          ${isMobile ? (isOpen ? 'translate-x-0' : '-translate-x-full') : 'translate-x-0'}
          md:translate-x-0
        `}
        aria-modal={isMobile && isOpen ? 'true' : undefined}
      >
        {/* Logo and Toggle */}
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <Link to="/" className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-lg">S</span>
              </div>
              <span
                className={`
                  font-bold text-xl text-gray-800 transition-opacity duration-300
                  ${isCollapsed ? 'opacity-0 w-0' : 'opacity-100'}
                `}
              >
                Speecher
              </span>
            </Link>
            <button
              onClick={handleToggleCollapse}
              className="p-1 rounded-lg hover:bg-gray-100 transition-colors"
              aria-label="Toggle sidebar"
              aria-expanded={!isCollapsed}
            >
              <svg
                className={`w-5 h-5 text-gray-600 transition-transform duration-300 ${isCollapsed ? 'rotate-180' : ''}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M11 19l-7-7 7-7m8 14l-7-7 7-7"
                />
              </svg>
            </button>
          </div>
        </div>

        {/* User Info */}
        {user && (
          <div className={`p-4 border-b border-gray-200 ${isCollapsed ? 'px-2' : ''}`}>
            <div className={`flex items-center space-x-3 ${isCollapsed ? 'justify-center' : ''}`}>
              <div className="w-10 h-10 bg-gradient-to-br from-blue-400 to-purple-500 rounded-full flex items-center justify-center">
                <span className="text-white font-semibold">
                  {user.name ? user.name[0].toUpperCase() : user.email[0].toUpperCase()}
                </span>
              </div>
              {!isCollapsed && (
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {user.name || 'User'}
                  </p>
                  <p className="text-xs text-gray-500 truncate">
                    {user.email}
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Navigation */}
        <nav
          className="flex-1 overflow-y-auto p-4"
          aria-label="Main navigation"
        >
          <Navigation items={navItems} isCollapsed={isCollapsed} />
        </nav>

        {/* Logout Button */}
        <div className="p-4 border-t border-gray-200">
          <button
            onClick={logout}
            className={`
              w-full flex items-center space-x-3 px-3 py-2 rounded-lg
              text-red-600 hover:bg-red-50 transition-colors
              ${isCollapsed ? 'justify-center' : 'justify-start'}
            `}
            aria-label="Logout"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
              />
            </svg>
            <span className={`${isCollapsed ? 'opacity-0 w-0' : 'opacity-100'} transition-opacity duration-300`}>
              Logout
            </span>
          </button>
        </div>
      </div>
    </>
  );
};

export default Sidebar;