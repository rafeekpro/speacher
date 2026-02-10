import axios from 'axios';
import { authService } from '../authService';
import { tokenStorage } from '../../utils/tokenStorage';

// Mock axios module
jest.mock('axios', () => ({
  post: jest.fn(),
  get: jest.fn(),
  create: jest.fn(() => ({
    interceptors: {
      request: { use: jest.fn() },
      response: { use: jest.fn() }
    }
  }))
}));
const mockedAxios = axios as jest.Mocked<typeof axios>;

// Mock tokenStorage
jest.mock('../../utils/tokenStorage');
const mockedTokenStorage = tokenStorage as jest.Mocked<typeof tokenStorage>;

describe('authService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('register', () => {
    it('should successfully register a new user', async () => {
      const userData = {
        email: 'test@example.com',
        password: 'password123',
        name: 'Test User'
      };
      const mockResponse = {
        data: {
          message: 'User registered successfully',
          user: { id: '123', email: userData.email, name: userData.name }
        }
      };

      mockedAxios.post.mockResolvedValueOnce(mockResponse);

      const result = await authService.register(userData);

      expect(mockedAxios.post).toHaveBeenCalledWith('/api/auth/register', userData);
      expect(result).toEqual(mockResponse.data);
    });

    it('should throw error on registration failure', async () => {
      const userData = {
        email: 'test@example.com',
        password: 'password123',
        name: 'Test User'
      };
      const errorMessage = 'Email already exists';
      
      mockedAxios.post.mockRejectedValueOnce({
        response: { data: { detail: errorMessage } }
      });

      await expect(authService.register(userData)).rejects.toThrow(errorMessage);
    });

    it('should throw generic error when no error message', async () => {
      const userData = {
        email: 'test@example.com',
        password: 'short',
        name: 'Test User'
      };
      
      mockedAxios.post.mockRejectedValueOnce(new Error('Network error'));

      await expect(authService.register(userData)).rejects.toThrow('Registration failed');
    });
  });

  describe('login', () => {
    it('should successfully login and store tokens', async () => {
      const credentials = {
        email: 'test@example.com',
        password: 'password123'
      };
      const mockResponse = {
        data: {
          access_token: 'access-token-123',
          refresh_token: 'refresh-token-456',
          token_type: 'Bearer'
        }
      };

      mockedAxios.post.mockResolvedValueOnce(mockResponse);

      const result = await authService.login(credentials);

      expect(mockedAxios.post).toHaveBeenCalledWith('/api/auth/login', credentials);
      expect(mockedTokenStorage.setAccessToken).toHaveBeenCalledWith('access-token-123');
      expect(mockedTokenStorage.setRefreshToken).toHaveBeenCalledWith('refresh-token-456');
      expect(result).toEqual(mockResponse.data);
    });

    it('should throw error on login failure', async () => {
      const credentials = {
        email: 'test@example.com',
        password: 'wrongpassword'
      };
      const errorMessage = 'Invalid credentials';
      
      mockedAxios.post.mockRejectedValueOnce({
        response: { data: { detail: errorMessage } }
      });

      await expect(authService.login(credentials)).rejects.toThrow(errorMessage);
      expect(mockedTokenStorage.setAccessToken).not.toHaveBeenCalled();
      expect(mockedTokenStorage.setRefreshToken).not.toHaveBeenCalled();
    });
  });

  describe('logout', () => {
    it('should successfully logout and clear tokens', async () => {
      mockedTokenStorage.getAccessToken.mockReturnValueOnce('access-token-123');
      mockedAxios.post.mockResolvedValueOnce({ data: { message: 'Logged out' } });

      await authService.logout();

      expect(mockedAxios.post).toHaveBeenCalledWith('/api/auth/logout', {}, {
        headers: { Authorization: 'Bearer access-token-123' }
      });
      expect(mockedTokenStorage.clearTokens).toHaveBeenCalled();
    });

    it('should clear tokens even if API call fails', async () => {
      // Mock console.error to avoid test output pollution
      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();
      
      mockedTokenStorage.getAccessToken.mockReturnValueOnce('access-token-123');
      mockedAxios.post.mockRejectedValueOnce(new Error('Network error'));

      await authService.logout();

      expect(mockedTokenStorage.clearTokens).toHaveBeenCalled();
      
      consoleErrorSpy.mockRestore();
    });

    it('should clear tokens even without access token', async () => {
      mockedTokenStorage.getAccessToken.mockReturnValueOnce(null);

      await authService.logout();

      expect(mockedAxios.post).not.toHaveBeenCalled();
      expect(mockedTokenStorage.clearTokens).toHaveBeenCalled();
    });
  });

  describe('refreshToken', () => {
    it('should successfully refresh access token', async () => {
      mockedTokenStorage.getRefreshToken.mockReturnValueOnce('refresh-token-456');
      const mockResponse = {
        data: {
          access_token: 'new-access-token-789',
          token_type: 'Bearer'
        }
      };

      mockedAxios.post.mockResolvedValueOnce(mockResponse);

      const result = await authService.refreshToken();

      expect(mockedAxios.post).toHaveBeenCalledWith('/api/auth/refresh', {
        refresh_token: 'refresh-token-456'
      });
      expect(mockedTokenStorage.setAccessToken).toHaveBeenCalledWith('new-access-token-789');
      expect(result).toEqual(mockResponse.data);
    });

    it('should throw error when no refresh token available', async () => {
      mockedTokenStorage.getRefreshToken.mockReturnValueOnce(null);

      await expect(authService.refreshToken()).rejects.toThrow('No refresh token available');
      expect(mockedAxios.post).not.toHaveBeenCalled();
    });

    it('should clear tokens on refresh failure', async () => {
      mockedTokenStorage.getRefreshToken.mockReturnValueOnce('invalid-refresh-token');
      mockedAxios.post.mockRejectedValueOnce({
        response: { data: { detail: 'Invalid refresh token' } }
      });

      await expect(authService.refreshToken()).rejects.toThrow('Invalid refresh token');
      expect(mockedTokenStorage.clearTokens).toHaveBeenCalled();
    });
  });

  describe('getCurrentUser', () => {
    it('should return user data from access token', () => {
      const mockPayload = {
        sub: 'user123',
        email: 'test@example.com',
        name: 'Test User',
        exp: Date.now() / 1000 + 3600
      };
      
      mockedTokenStorage.getAccessToken.mockReturnValueOnce('access-token');
      mockedTokenStorage.getTokenPayload.mockReturnValueOnce(mockPayload);

      const user = authService.getCurrentUser();

      expect(user).toEqual({
        id: 'user123',
        email: 'test@example.com',
        name: 'Test User'
      });
    });

    it('should return null when no access token', () => {
      mockedTokenStorage.getAccessToken.mockReturnValueOnce(null);

      const user = authService.getCurrentUser();

      expect(user).toBeNull();
      expect(mockedTokenStorage.getTokenPayload).not.toHaveBeenCalled();
    });

    it('should return null when token payload is invalid', () => {
      mockedTokenStorage.getAccessToken.mockReturnValueOnce('access-token');
      mockedTokenStorage.getTokenPayload.mockReturnValueOnce(null);

      const user = authService.getCurrentUser();

      expect(user).toBeNull();
    });
  });

  describe('isAuthenticated', () => {
    it('should return true when valid access token exists', () => {
      mockedTokenStorage.getAccessToken.mockReturnValueOnce('access-token');
      mockedTokenStorage.isTokenExpired.mockReturnValueOnce(false);

      expect(authService.isAuthenticated()).toBe(true);
    });

    it('should return false when no access token', () => {
      mockedTokenStorage.getAccessToken.mockReturnValueOnce(null);

      expect(authService.isAuthenticated()).toBe(false);
    });

    it('should return false when token is expired', () => {
      mockedTokenStorage.getAccessToken.mockReturnValueOnce('expired-token');
      mockedTokenStorage.isTokenExpired.mockReturnValueOnce(true);

      expect(authService.isAuthenticated()).toBe(false);
    });
  });
});