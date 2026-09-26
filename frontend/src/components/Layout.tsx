import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const NAV = [
    { to: "/", label: "Dashboard", end: true },
    { to: "/inventory", label: "Inventory" },
    { to: "/billing", label: "Billing" },
    { to: "/orders", label: "Orders" },
    { to: "/alerts", label: "Low-Stock Alerts" },
];

/** App shell: sidebar navigation + header + routed content. */
export default function Layout() {
    const { user, logout } = useAuth();
    const navigate = useNavigate();

    const handleLogout = () => {
        logout();
        navigate("/login");
    };

    return (
        <div className="app-shell">
            <aside className="sidebar">
                <div className="brand">
                    <span className="brand-mark">📦</span>
                    <div>
                        <div className="brand-name">Inventory Mama</div>
                        <div className="brand-sub">Billing & Stock</div>
                    </div>
                </div>
                <nav className="nav">
                    {NAV.map((item) => (
                        <NavLink
                            key={item.to}
                            to={item.to}
                            end={item.end}
                            className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
                        >
                            {item.label}
                        </NavLink>
                    ))}
                </nav>
                <div className="sidebar-footer">
                    <div className="user-chip">
                        <div className="avatar">{(user?.username || "?").charAt(0).toUpperCase()}</div>
                        <div>
                            <div className="user-name">{user?.full_name || user?.username}</div>
                            <div className="user-role">{user?.is_owner ? "Owner" : "Staff"}</div>
                        </div>
                    </div>
                    <button className="btn btn-ghost" onClick={handleLogout}>
                        Sign out
                    </button>
                </div>
            </aside>
            <main className="content">
                <Outlet />
            </main>
        </div>
    );
}
