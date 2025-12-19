import { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import { endpoints } from '../services/api';

interface User {
    email: string;
    role: string;
}

interface AuthContextType {
    user: User | null;
    isAuthenticated: boolean;
    isLoading: boolean;
    login: (email: string, password: string) => Promise<void>;
    logout: () => Promise<void>;
    register: (email: string, password: string) => Promise<void>;
    refreshToken: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const TOKEN_KEY = 'co_counsel_token';
const REFRESH_TOKEN_KEY = 'co_counsel_refresh_token';
const USER_KEY = 'co_counsel_user';

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(() => {
        const stored = localStorage.getItem(USER_KEY);
        return stored ? JSON.parse(stored) : null;
    });
    const [isLoading, setIsLoading] = useState(true);

    // Check token validity on mount
    useEffect(() => {
        const token = localStorage.getItem(TOKEN_KEY);
        if (token) {
            // Validate token by fetching current user
            fetchCurrentUser().finally(() => setIsLoading(false));
        } else {
            setIsLoading(false);
        }
    }, []);

    const fetchCurrentUser = async () => {
        try {
            const response = await endpoints.auth.me();
            const userData = response.data;
            setUser(userData);
            localStorage.setItem(USER_KEY, JSON.stringify(userData));
        } catch (error) {
            // Token invalid or expired, try refresh
            const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
            if (refreshToken) {
                try {
                    await doRefreshToken();
                    const response = await endpoints.auth.me();
                    setUser(response.data);
                    localStorage.setItem(USER_KEY, JSON.stringify(response.data));
                } catch {
                    clearAuth();
                }
            } else {
                clearAuth();
            }
        }
    };

    const clearAuth = () => {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(REFRESH_TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
        setUser(null);
    };

    const login = useCallback(async (email: string, password: string) => {
        setIsLoading(true);
        try {
            const response = await endpoints.auth.login(email, password);
            const { access_token, refresh_token } = response.data;

            localStorage.setItem(TOKEN_KEY, access_token);
            if (refresh_token) {
                localStorage.setItem(REFRESH_TOKEN_KEY, refresh_token);
            }

            // Fetch user data
            const userResponse = await endpoints.auth.me();
            setUser(userResponse.data);
            localStorage.setItem(USER_KEY, JSON.stringify(userResponse.data));
        } finally {
            setIsLoading(false);
        }
    }, []);

    const logout = useCallback(async () => {
        try {
            await endpoints.auth.logout();
        } catch {
            // Ignore logout errors
        } finally {
            clearAuth();
        }
    }, []);

    const register = useCallback(async (email: string, password: string) => {
        setIsLoading(true);
        try {
            await endpoints.auth.register(email, password);
            // Auto-login after registration
            await login(email, password);
        } finally {
            setIsLoading(false);
        }
    }, [login]);

    const doRefreshToken = async () => {
        const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
        if (!refreshToken) throw new Error('No refresh token');

        const response = await endpoints.auth.refresh(refreshToken);
        const { access_token, refresh_token: newRefreshToken } = response.data;

        localStorage.setItem(TOKEN_KEY, access_token);
        if (newRefreshToken) {
            localStorage.setItem(REFRESH_TOKEN_KEY, newRefreshToken);
        }
    };

    const refreshTokenCallback = useCallback(async () => {
        await doRefreshToken();
    }, []);

    const value: AuthContextType = {
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        logout,
        register,
        refreshToken: refreshTokenCallback,
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth(): AuthContextType {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}

// Helper to get token for API calls
export function getAuthToken(): string | null {
    return localStorage.getItem(TOKEN_KEY);
}
