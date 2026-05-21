"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { getCurrentUser, loginAccount, registerAccount } from "@/lib/api";
import type { User } from "@/lib/types";

const TOKEN_STORAGE_KEY = "nexterview.accessToken";

type LoginInput = {
  email: string;
  password: string;
};

type RegisterInput = {
  email: string;
  password: string;
  full_name: string;
  organization_name: string;
};

type AuthContextValue = {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (input: LoginInput) => Promise<void>;
  register: (input: RegisterInput) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const applySession = useCallback((nextToken: string, nextUser: User) => {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, nextToken);
    setToken(nextToken);
    setUser(nextUser);
  }, []);

  const logout = useCallback(() => {
    window.localStorage.removeItem(TOKEN_STORAGE_KEY);
    setToken(null);
    setUser(null);
  }, []);

  useEffect(() => {
    let isMounted = true;
    const savedToken = window.localStorage.getItem(TOKEN_STORAGE_KEY);
    if (!savedToken) {
      setIsLoading(false);
      return;
    }

    setToken(savedToken);
    getCurrentUser(savedToken)
      .then((currentUser) => {
        if (isMounted) {
          setUser(currentUser);
        }
      })
      .catch(() => {
        if (isMounted) {
          logout();
        }
      })
      .finally(() => {
        if (isMounted) {
          setIsLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [logout]);

  const login = useCallback(
    async (input: LoginInput) => {
      const response = await loginAccount(input);
      applySession(response.access_token, response.user);
    },
    [applySession],
  );

  const register = useCallback(
    async (input: RegisterInput) => {
      const response = await registerAccount(input);
      applySession(response.access_token, response.user);
    },
    [applySession],
  );

  const value = useMemo(
    () => ({ user, token, isLoading, login, register, logout }),
    [isLoading, login, logout, register, token, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used inside AuthProvider.");
  }
  return context;
}
