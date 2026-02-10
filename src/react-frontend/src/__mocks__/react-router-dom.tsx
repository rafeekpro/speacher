import React from 'react';

export const Link = ({ children, to, ...props }: any) => (
  <a href={to} {...props}>{children}</a>
);

export const useLocation = jest.fn(() => ({ 
  pathname: '/',
  search: '',
  hash: '',
  state: null
}));

export const MemoryRouter = ({ children }: any) => <>{children}</>;
export const BrowserRouter = ({ children }: any) => <>{children}</>;
export const Navigate = ({ to }: any) => <div>Navigate to {to}</div>;

// Add missing Route and Routes components for react-router-dom v7
export const Routes = ({ children }: any) => <>{children}</>;
export const Route = ({ element }: any) => <>{element}</>;

// Add other commonly used exports
export const useNavigate = jest.fn(() => jest.fn());
export const useParams = jest.fn(() => ({}));
export const useSearchParams = jest.fn(() => [new URLSearchParams(), jest.fn()]);
export const Outlet = () => <div data-testid="outlet" />;