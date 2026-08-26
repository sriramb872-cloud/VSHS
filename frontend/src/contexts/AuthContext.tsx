// frontend/src/context/AuthContext.tsx
import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { api } from '../services/api';
import { authService } from '../services/auth';

export interface User {
  id: number;
  school_id: number | null;
  mobile: string;
  display_name: string;
  role: 'SUPER_ADMIN' | 'PRINCIPAL' | 'TEACHER' | 'STUDENT';
  is_active: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: (mobile: string, password: string) => Promise<User>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('scholaris_access_token'));
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const initAuth = async () => {
      const storedToken = localStorage.getItem('scholaris_access_token');
      if (!storedToken) {
        setLoading(false);
        return;
      }
      try {
        const response = await api.get<User>('/auth/me');
        setUser(response.data);
        setToken(storedToken);
      } catch (err) {
        localStorage.removeItem('scholaris_access_token');
        setToken(null);
        setUser(null);
      } finally {
        setLoading(false);
      }
    };

    initAuth();
  }, []);

  const login = async (mobile: string, password: string): Promise<User> => {
    const response = await authService.login({ mobile, password });
    const accessToken = response.access_token;

    localStorage.setItem('scholaris_access_token', accessToken);
    setToken(accessToken);

    const userResponse = await api.get<User>('/auth/me');
    setUser(userResponse.data);
    return userResponse.data;
  };

  const logout = () => {
    authService.logout();
    setToken(null);
    setUser(null);
    window.location.href = '/login';
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        isAuthenticated: !!user,
        login,
        logout,
      }}
    >
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
