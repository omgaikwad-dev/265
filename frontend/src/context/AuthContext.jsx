import React, { createContext, useContext, useState, useEffect } from 'react';
import { authService } from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('fdrsetu_user');
    return saved ? JSON.parse(saved) : null;
  });
  const [token, setToken] = useState(() => localStorage.getItem('fdrsetu_token'));
  const [loading, setLoading] = useState(true);
  const [demoAccounts, setDemoAccounts] = useState([]);

  useEffect(() => {
    const initAuth = async () => {
      const storedToken = localStorage.getItem('fdrsetu_token');
      if (storedToken) {
        try {
          const profile = await authService.getMe();
          setUser(profile);
          localStorage.setItem('fdrsetu_user', JSON.stringify(profile));
        } catch (err) {
          console.warn("Session restore failed, logging out:", err);
          logout();
        }
      }
      try {
        const demos = await authService.getDemoAccounts();
        setDemoAccounts(demos);
      } catch (e) {
        console.error("Could not fetch demo accounts:", e);
      } finally {
        setLoading(false);
      }
    };
    initAuth();
  }, []);

  const login = async (usernameOrEmail, password) => {
    const data = await authService.login(usernameOrEmail, password);
    setToken(data.access_token);
    setUser(data.user);
    localStorage.setItem('fdrsetu_token', data.access_token);
    localStorage.setItem('fdrsetu_refresh_token', data.refresh_token);
    localStorage.setItem('fdrsetu_user', JSON.stringify(data.user));
    return data.user;
  };

  const logout = async () => {
    try {
      if (token) {
        await authService.logout();
      }
    } catch (e) {
      // ignore
    } finally {
      setUser(null);
      setToken(null);
      localStorage.removeItem('fdrsetu_token');
      localStorage.removeItem('fdrsetu_refresh_token');
      localStorage.removeItem('fdrsetu_user');
    }
  };

  const register = async (regData) => {
    return await authService.registerInstitution(regData);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user,
        role: user?.role?.name || null,
        institution: user?.institution || null,
        loading,
        demoAccounts,
        login,
        logout,
        register,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
