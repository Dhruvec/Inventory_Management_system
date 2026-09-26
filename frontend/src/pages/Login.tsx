import { useState } from "react";
import { useAuth } from "../context/AuthContext";

/** Login / first-run registration screen. */
export default function Login() {
    const { login, register } = useAuth();
    const [mode, setMode] = useState<"login" | "register">("login");
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [fullName, setFullName] = useState("");
    const [error, setError] = useState<string | null>(null);
    const [busy, setBusy] = useState(false);

    const submit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setBusy(true);
        try {
            if (mode === "login") await login(username, password);
            else await register(username, password, fullName || undefined);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Something went wrong");
        } finally {
            setBusy(false);
        }
    };

    return (
        <div className="login-screen">
            <div className="login-card">
                <div className="login-brand">
                    <span className="brand-mark">📦</span>
                    <div>
                        <h1>Inventory Mama</h1>
                        <p>Small-business inventory & billing</p>
                    </div>
                </div>

                <div className="tabs">
                    <button
                        className={mode === "login" ? "tab active" : "tab"}
                        onClick={() => setMode("login")}
                        type="button"
                    >
                        Sign in
                    </button>
                    <button
                        className={mode === "register" ? "tab active" : "tab"}
                        onClick={() => setMode("register")}
                        type="button"
                    >
                        Register
                    </button>
                </div>

                <form onSubmit={submit} className="form">
                    {mode === "register" && (
                        <label className="field">
                            <span>Full name</span>
                            <input
                                value={fullName}
                                onChange={(e) => setFullName(e.target.value)}
                                placeholder="Shop Owner"
                            />
                        </label>
                    )}
                    <label className="field">
                        <span>Username</span>
                        <input
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            required
                            autoFocus
                        />
                    </label>
                    <label className="field">
                        <span>Password</span>
                        <input
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                        />
                    </label>

                    {error && <div className="alert-error">{error}</div>}

                    <button className="btn btn-primary" disabled={busy} type="submit">
                        {busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
                    </button>
                </form>

                {mode === "login" && (
                    <p className="login-hint">
                        First run? Register — the first account becomes the owner. Demo seed
                        user: <code>owner / owner123</code>
                    </p>
                )}
            </div>
        </div>
    );
}
