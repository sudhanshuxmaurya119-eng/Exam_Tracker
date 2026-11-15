import React, { createContext, useContext, useEffect, useState } from "react";
import { AdminUser } from "../types";
import {
  apiClient,
  clearStoredSession,
  getStoredToken,
  getStoredUser,
  setStoredSession,
} from "../api/client";

interface AuthContextValue {
  admin: AdminUser | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [admin, setAdmin] = useState<AdminUser | null>(() => getStoredUser());
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const token = getStoredToken();
    if (!token) {
      setLoading(false);
      return;
    }
    apiClient
      .getMe()
      .then((user) => {
        setAdmin(user);
      })
      .catch(() => {
        clearStoredSession();
        setAdmin(null);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  const login = async (username: string, password: string) => {
    const res = await apiClient.login(username, password);
    setStoredSession(res.access_token, res.user);
    setAdmin(res.user);
  };

  const logout = () => {
    clearStoredSession();
    setAdmin(null);
  };

  return (
    <AuthContext.Provider value={{ admin, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
