import React, { createContext, useContext, useState, useEffect } from 'react';
import { User } from '../types/common';
import { LoginCredentials, RegisterCredentials, AuthState } from '../types/auth';
import { authService } from '../services/authService';

interface AuthContextType extends AuthState {
  login: (credentials: LoginCredentials) => Promise<void>;
  register: (credentials: RegisterCredentials) => Promise<void>;
  logout: () => Promise<void>;
  forgotPassword: (email: string) => Promise<{ success: boolean; message: string }>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [authState, setAuthState] = useState<AuthState>({
    user: null,
    isAuthenticated: false,
    isLoading: true,
    token: null,
  });

  useEffect(() => {
    // Check initial session
    const stored = authService.getStoredSession();
    if (stored && stored.user && stored.token) {
      setAuthState({
        user: stored.user,
        isAuthenticated: true,
        isLoading: false,
        token: stored.token,
      });
    } else {
      setAuthState((prev) => ({ ...prev, isLoading: false }));
    }
  }, []);

  const login = async (credentials: LoginCredentials) => {
    const res = await authService.login(credentials);
    if (res.error || !res.data) {
      throw new Error(res.error || 'Login failed');
    }
    setAuthState({
      user: res.data.user,
      isAuthenticated: true,
      isLoading: false,
      token: res.data.token,
    });
  };

  const register = async (credentials: RegisterCredentials) => {
    const res = await authService.register(credentials);
    if (res.error || !res.data) {
      throw new Error(res.error || 'Registration failed');
    }
    setAuthState({
      user: res.data.user,
      isAuthenticated: true,
      isLoading: false,
      token: res.data.token,
    });
  };

  const logout = async () => {
    await authService.logout();
    setAuthState({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      token: null,
    });
  };

  const forgotPassword = async (email: string) => {
    const res = await authService.forgotPassword({ email });
    if (res.error || !res.data) {
      throw new Error(res.error || 'Password reset failed');
    }
    return res.data;
  };

  return (
    <AuthContext.Provider value={{ ...authState, login, register, logout, forgotPassword }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
