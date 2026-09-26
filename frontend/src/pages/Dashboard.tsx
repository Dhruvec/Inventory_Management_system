import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import StatCard from "../components/StatCard";
import type { DashboardSummary, LowStockAlert } from "../types";
import { currency } from "../utils/format";

/** Landing dashboard: KPIs + a live low-stock preview. */
export default function Dashboard() {
    const [summary, setSummary] = useState<DashboardSummary | null>(null);
    const [alerts, setAlerts] = useState<LowStockAlert[]>([]);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        Promise.all([api.dashboardSummary(), api.lowStockAlerts()])
            .then(([s, a]) => {
                setSummary(s);
                setAlerts(a);
            })
            .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"));
    }, []);

    if (error) return <div className="alert-error">{error}</div>;
    if (!summary) return <div className="page-loading">Loading dashboard…</div>;

    return (
        <div className="page">
            <header className="page-header">
                <div>
                    <h2>Dashboard</h2>
                    <p className="muted">A snapshot of today's shop performance.</p>
                </div>
                <Link className="btn btn-primary" to="/billing">
                    + New sale
                </Link>
            </header>

            <section className="stat-grid">
                <StatCard label="Revenue (confirmed)" value={currency(summary.total_revenue)} tone="good" />
                <StatCard
                    label="Outstanding balance"
                    value={currency(summary.outstanding_balance)}
                    tone={summary.outstanding_balance > 0 ? "warn" : "default"}
                />
                <StatCard label="Inventory value" value={currency(summary.inventory_value)} />
                <StatCard
                    label="Low-stock items"
                    value={summary.low_stock_count}
                    tone={summary.low_stock_count > 0 ? "warn" : "good"}
                />
                <StatCard label="Products" value={summary.total_products} hint={`${summary.active_products} active`} />
                <StatCard
                    label="Orders"
                    value={summary.total_orders}
                    hint={`${summary.confirmed_orders} confirmed · ${summary.cancelled_orders} cancelled`}
                />
            </section>

            <section className="card">
                <div className="card-header">
                    <h3>Needs restocking</h3>
                    <Link to="/alerts" className="link">
                        View all
                    </Link>
                </div>
                {alerts.length === 0 ? (
                    <p className="muted empty-state">Everything is well stocked. 🎉</p>
                ) : (
                    <table className="table">
                        <thead>
                            <tr>
                                <th>Product</th>
                                <th>SKU</th>
                                <th className="num">In stock</th>
                                <th className="num">Threshold</th>
                                <th className="num">Deficit</th>
                            </tr>
                        </thead>
                        <tbody>
                            {alerts.slice(0, 6).map((a) => (
                                <tr key={a.product_id}>
                                    <td>{a.name}</td>
                                    <td className="mono">{a.sku}</td>
                                    <td className="num">{a.quantity_in_stock}</td>
                                    <td className="num">{a.low_stock_threshold}</td>
                                    <td className="num">
                                        <span className="badge badge-warn">−{a.deficit}</span>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </section>
        </div>
    );
}
