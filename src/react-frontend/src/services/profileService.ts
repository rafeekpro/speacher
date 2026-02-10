import axios from 'axios';

export interface UserProfile {
  id: string;
  email: string;
  name: string;
  bio?: string;
  phone?: string;
  location?: string;
  language?: string;
  timezone?: string;
  createdAt: string;
  updatedAt: string;
}

export interface UpdateProfileData {
  name?: string;
  bio?: string;
  phone?: string;
  location?: string;
  language?: string;
  timezone?: string;
}

export interface UpdatePasswordData {
  currentPassword: string;
  newPassword: string;
}

export interface ApiKey {
  id: string;
  name: string;
  key?: string; // Only returned on creation
  maskedKey: string;
  createdAt: string;
  lastUsed?: string;
  expiresAt?: string;
}

export interface CreateApiKeyData {
  name: string;
  expiresIn?: number; // Days until expiration
}

export interface UserPreferences {
  emailNotifications: boolean;
  pushNotifications: boolean;
  theme: 'light' | 'dark' | 'system';
  autoSave: boolean;
  transcriptionLanguage: string;
  defaultModel: string;
}

class ProfileService {
  async getProfile(): Promise<UserProfile> {
    try {
      const response = await axios.get<UserProfile>('/api/user/profile');
      return response.data;
    } catch (error: any) {
      if (error?.response?.data?.detail) {
        throw new Error(error.response.data.detail);
      }
      throw new Error('Failed to load profile');
    }
  }

  async updateProfile(data: UpdateProfileData): Promise<UserProfile> {
    try {
      const response = await axios.put<UserProfile>('/api/user/profile', data);
      return response.data;
    } catch (error: any) {
      if (error?.response?.data?.detail) {
        throw new Error(error.response.data.detail);
      }
      throw new Error('Failed to update profile');
    }
  }

  async updatePassword(data: UpdatePasswordData): Promise<void> {
    try {
      await axios.post('/api/user/change-password', data);
    } catch (error: any) {
      if (error?.response?.data?.detail) {
        throw new Error(error.response.data.detail);
      }
      throw new Error('Failed to update password');
    }
  }

  async getApiKeys(): Promise<ApiKey[]> {
    try {
      const response = await axios.get<ApiKey[]>('/api/user/api-keys');
      return response.data;
    } catch (error: any) {
      if (error?.response?.data?.detail) {
        throw new Error(error.response.data.detail);
      }
      throw new Error('Failed to load API keys');
    }
  }

  async createApiKey(data: CreateApiKeyData): Promise<ApiKey> {
    try {
      const response = await axios.post<ApiKey>('/api/user/api-keys', data);
      return response.data;
    } catch (error: any) {
      if (error?.response?.data?.detail) {
        throw new Error(error.response.data.detail);
      }
      throw new Error('Failed to create API key');
    }
  }

  async deleteApiKey(id: string): Promise<void> {
    try {
      await axios.delete(`/api/user/api-keys/${id}`);
    } catch (error: any) {
      if (error?.response?.data?.detail) {
        throw new Error(error.response.data.detail);
      }
      throw new Error('Failed to delete API key');
    }
  }

  async getPreferences(): Promise<UserPreferences> {
    try {
      const response = await axios.get<UserPreferences>('/api/user/preferences');
      return response.data;
    } catch (error: any) {
      if (error?.response?.data?.detail) {
        throw new Error(error.response.data.detail);
      }
      throw new Error('Failed to load preferences');
    }
  }

  async updatePreferences(data: Partial<UserPreferences>): Promise<UserPreferences> {
    try {
      const response = await axios.patch<UserPreferences>('/api/user/preferences', data);
      return response.data;
    } catch (error: any) {
      if (error?.response?.data?.detail) {
        throw new Error(error.response.data.detail);
      }
      throw new Error('Failed to update preferences');
    }
  }
}

export const profileService = new ProfileService();