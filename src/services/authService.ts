import { apiClient, ApiResponse } from './apiClient';
import { LoginCredentials, RegisterCredentials, ForgotPasswordRequest, AuthSession } from '../types/auth';
import { mockCurrentUser, mockUsers } from '../data/mockData';

const SESSION_KEY = 'kh_auth_session';
const TOKEN_KEY = 'kh_auth_token';

class AuthService {
  async login(credentials: LoginCredentials): Promise<ApiResponse<AuthSession>> {
    return apiClient.executeMock(() => {
      if (!credentials.email || !credentials.password) {
        throw new Error('Please provide both email and password.');
      }

      // Check format
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(credentials.email)) {
        throw new Error('Please enter a valid work or academic email address.');
      }

      if (credentials.password.length < 6) {
        throw new Error('Password must be at least 6 characters long.');
      }

      const foundUser = mockUsers.find(
        (u) => u.email.toLowerCase() === credentials.email.toLowerCase()
      ) || {
        ...mockCurrentUser,
        email: credentials.email,
        name: credentials.email.split('@')[0].replace('.', ' '),
      };

      const session: AuthSession = {
        user: foundUser,
        token: `kh_jwt_${Date.now()}_${Math.random().toString(36).substring(7)}`,
        expiresAt: new Date(Date.now() + 86400 * 1000 * 7).toISOString(),
      };

      localStorage.setItem(SESSION_KEY, JSON.stringify(session));
      localStorage.setItem(TOKEN_KEY, session.token);

      return session;
    });
  }

  async register(credentials: RegisterCredentials): Promise<ApiResponse<AuthSession>> {
    return apiClient.executeMock(() => {
      if (!credentials.fullName || !credentials.email || !credentials.password) {
        throw new Error('Please fill in all required registration fields.');
      }

      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(credentials.email)) {
        throw new Error('Please enter a valid email address.');
      }

      if (credentials.password.length < 8) {
        throw new Error('Password must be at least 8 characters with letters and numbers.');
      }

      if (credentials.confirmPassword && credentials.password !== credentials.confirmPassword) {
        throw new Error('Passwords do not match.');
      }

      const newUser = {
        id: `usr-${Date.now()}`,
        name: credentials.fullName,
        email: credentials.email,
        role: 'engineer' as const,
        department: credentials.organization || 'Engineering',
        lastActive: 'Just now',
        avatarUrl: `https://api.dicebear.com/7.x/initials/svg?seed=${encodeURIComponent(credentials.fullName)}`,
      };

      const session: AuthSession = {
        user: newUser,
        token: `kh_jwt_${Date.now()}_${Math.random().toString(36).substring(7)}`,
        expiresAt: new Date(Date.now() + 86400 * 1000 * 7).toISOString(),
      };

      localStorage.setItem(SESSION_KEY, JSON.stringify(session));
      localStorage.setItem(TOKEN_KEY, session.token);

      return session;
    });
  }

  async forgotPassword(request: ForgotPasswordRequest): Promise<ApiResponse<{ success: boolean; message: string }>> {
    return apiClient.executeMock(() => {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!request.email || !emailRegex.test(request.email)) {
        throw new Error('Please provide a valid account email.');
      }

      return {
        success: true,
        message: `Password reset instructions have been dispatched to ${request.email}. Please verify your inbox.`,
      };
    });
  }

  getStoredSession(): AuthSession | null {
    try {
      const raw = localStorage.getItem(SESSION_KEY);
      if (!raw) return null;
      return JSON.parse(raw);
    } catch {
      return null;
    }
  }

  async logout(): Promise<void> {
    localStorage.removeItem(SESSION_KEY);
    localStorage.removeItem(TOKEN_KEY);
  }
}

export const authService = new AuthService();
