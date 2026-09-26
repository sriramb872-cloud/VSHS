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
  must_change_password?: boolean;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  isAuthenticated: boolean;
  mustChangePassword: boolean;
  login: (mobile: string, password: string) => Promise<User>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('scholaris_access_token'));
  const [loading, setLoading] = useState<boolean>(true);
  const [mustChangePassword, setMustChangePassword] = useState<boolean>(false);

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
        setMustChangePassword(!!response.data.must_change_password);
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
    setMustChangePassword(!!response.must_change_password || !!userResponse.data.must_change_password);
    window.dispatchEvent(new Event('scholaris:pet-greeting'));
    return userResponse.data;
  };

  const changePassword = async (currentPassword: string, newPassword: string): Promise<void> => {
    await authService.changePassword(currentPassword, newPassword);
    setMustChangePassword(false);
    if (user) {
      const userResponse = await api.get<User>('/auth/me');
      setUser(userResponse.data);
    }
  };

  const logout = () => {
    window.dispatchEvent(new Event('scholaris:pet-farewell'));
    authService.logout();
    window.setTimeout(() => {
      setToken(null);
      setUser(null);
      window.location.href = '/login';
    }, 1500);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        isAuthenticated: !!user,
        mustChangePassword,
        login,
        changePassword,
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
