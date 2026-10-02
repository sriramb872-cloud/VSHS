// frontend/src/context/AuthContext.tsx
import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { api, getAccessToken, getRefreshToken, setTokens, clearTokens } from '../services/api';
import { authService } from '../services/auth';

export interface User {
  id: number;
  school_id: number | null;
  mobile: string;
  email?: string | null;
  display_name: string;
  role: 'SUPER_ADMIN' | 'PRINCIPAL' | 'TEACHER' | 'STUDENT';
  is_active: string;
  must_change_password?: boolean;
  /**
   * Path under `/media`, e.g. `/media/profile_photos/photo_user_10_ab12cd34.png`.
   * Set by `POST /files/profile-photo` and returned by `GET /users/me`.
   */
  profile_photo?: string | null;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  isAuthenticated: boolean;
  mustChangePassword: boolean;
  login: (mobile: string, password: string) => Promise<User>;
  refreshUser: () => Promise<User | null>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(getAccessToken());
  const [loading, setLoading] = useState<boolean>(true);
  const [mustChangePassword, setMustChangePassword] = useState<boolean>(false);

  useEffect(() => {
    const initAuth = async () => {
      const storedToken = getAccessToken();
      const storedRefresh = getRefreshToken();

      // No access token but a refresh token (e.g. the tab was reopened after
      // the access token expired): restore the session server-side first.
      if (!storedToken && storedRefresh) {
        try {
          await authService.refresh(storedRefresh);
        } catch {
          clearTokens();
          setLoading(false);
          return;
        }
      } else if (!storedToken) {
        setLoading(false);
        return;
      }

      try {
        const response = await api.get<User>('/auth/me');
        setUser(response.data);
        setMustChangePassword(!!response.data.must_change_password);
        setToken(getAccessToken());
      } catch (err) {
        clearTokens();
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

    // Persist the full pair: the access token for API calls, the rotating
    // refresh token to renew it transparently when it expires.
    setTokens(accessToken, response.refresh_token);
    setToken(accessToken);

    const userResponse = await api.get<User>('/auth/me');
    setUser(userResponse.data);
    setMustChangePassword(!!response.must_change_password || !!userResponse.data.must_change_password);
    // Let dependent providers (e.g. AcademicYearContext) know they can now
    // fetch school-scoped data without a 401.
    window.dispatchEvent(new Event('scholaris:auth-changed'));
    window.dispatchEvent(new Event('scholaris:pet-greeting'));
    return userResponse.data;
  };

  /**
   * Re-read the current user from the server. Used after a profile edit so the
   * header/sidebar name and email stay in sync with what was just saved.
   */
  const refreshUser = async (): Promise<User | null> => {
    try {
      const response = await api.get<User>('/auth/me');
      setUser(response.data);
      setMustChangePassword(!!response.data.must_change_password);
      return response.data;
    } catch {
      return null;
    }
  };

  const changePassword = async (currentPassword: string, newPassword: string): Promise<void> => {
    // Changing the password revokes every other session server-side and
    // returns a fresh token pair for THIS client - store it, otherwise the
    // stored access token is already invalid and the user is bounced to login
    // right after a successful change.
    const result = await authService.changePassword(currentPassword, newPassword);
    if (result?.access_token) {
      setTokens(result.access_token, result.refresh_token);
      setToken(result.access_token);
    }
    setMustChangePassword(false);
    if (user) {
      const userResponse = await api.get<User>('/auth/me');
      setUser(userResponse.data);
    }
  };

  const logout = () => {
    window.dispatchEvent(new Event('scholaris:pet-farewell'));
    // Revoke server-side first (fire-and-forget with a timeout guard so a
    // hung network can never block the local sign-out), then clear locally.
    const refresh = getRefreshToken();
    authService.logout(refresh).finally(() => {
      clearTokens();
    });
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
        refreshUser,
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
