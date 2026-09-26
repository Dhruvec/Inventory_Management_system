import {
    createContext,
    useContext,
    useEffect,
    useState,
    type ReactNode,
} from "react";
import { api, getToken, setToken } from "../api";
import type { User } from "../types";

interface AuthState {
    user: User | null;
    loading: boolean;
    login: (username: string, password: string) => Promise<void>;
    register: (username: string, password: string, fullName?: string) => Promise<void>;
    logout: () => void;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // Restore the session if a token is already stored.
        if (!getToken()) {
            setLoading(false);
            return;
        }
        api
            .me()
            .then(setUser)
            .catch(() => setToken(null))
            .finally(() => setLoading(false));
    }, []);

    const login = async (username: string, password: string) => {
        await api.login(username, password);
        setUser(await api.me());
    };

    const register = async (username: string, password: string, fullName?: string) => {
        await api.register({ username, password, full_name: fullName });
        await login(username, password);
    };

    const logout = () => {
        setToken(null);
        setUser(null);
    };

    return (
        <AuthContext.Provider value={{ user, loading, login, register, logout }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth(): AuthState {
    const ctx = useContext(AuthContext);
    if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
    return ctx;
}
