import { User } from './common';

export interface LoginCredentials {
  email: string;
  password: string;
  rememberMe?: boolean;
}

export interface RegisterCredentials {
  fullName: string;
  email: string;
  password: string;
  confirmPassword?: string;
  organization?: string;
}

export interface ForgotPasswordRequest {
  email: string;
}

export interface AuthSession {
  user: User;
  token: string;
  expiresAt: string;
}

export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  token: string | null;
}
