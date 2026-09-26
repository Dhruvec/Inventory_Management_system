import { useEffect, useState } from "react";
import { api } from "../api";
import Modal from "../components/Modal";
import type { LowStockAlert } from "../types";

/** Low-stock alert centre with a quick-restock action. */
export default function Alerts() {
    const [alerts, setAlerts] = useState<LowStockAlert[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [restockTarget, setRestockTarget] = useState<LowStockAlert | null>(null);
    const [amount, setAmount] = useState(0);

    const load = () =>
        api
            .lowStockAlerts()
            .then(setAlerts)
            .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"));

    useEffect(() => {
        load();
    }, []);

    const submitRestock = async () => {
        if (!restockTarget || amount <= 0) return;
        try {
            await api.adjustStock(restockTarget.product_id, amount, "purchase", "Quick restock");
            setRestockTarget(null);
            setAmount(0);
            await load();
        } catch (e) {
            setError(e instanceof Error ? e.message : "Restock failed");
        }
    };

    return (
        <div className="page">
            <header className="page-header">
                <div>
                    <h2>Low-Stock Alerts</h2>
                    <p className="muted">Items at or below their reorder threshold.</p>
                </div>
            </header>

            {error && <div className="alert-error">{error}</div>}

            <section className="card">
                {alerts.length === 0 ? (
                    <p className="muted empty-state">No low-stock items right now. 🎉</p>
                ) : (
                    <table className="table">
                        <thead>
                            <tr>
                                <th>Product</th>
                                <th>SKU</th>
                                <th className="num">In stock</th>
                                <th className="num">Threshold</th>
                                <th className="num">Deficit</th>
                                <th />
                            </tr>
                        </thead>
                        <tbody>
                            {alerts.map((a) => (
                                <tr key={a.product_id}>
                                    <td>{a.name}</td>
                                    <td className="mono">{a.sku}</td>
                                    <td className="num">{a.quantity_in_stock}</td>
                                    <td className="num">{a.low_stock_threshold}</td>
                                    <td className="num">
                                        <span className="badge badge-warn">−{a.deficit}</span>
                                    </td>
                                    <td className="num">
                                        <button
                                            className="btn btn-small"
                                            onClick={() => {
                                                setRestockTarget(a);
                                                setAmount(a.deficit || a.low_stock_threshold);
                                            }}
                                        >
                                            Restock
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </section>

            {restockTarget && (
                <Modal title={`Restock: ${restockTarget.name}`} onClose={() => setRestockTarget(null)}>
                    <div className="form">
                        <label className="field">
                            <span>Quantity to add</span>
                            <input
                                type="number"
                                min={1}
                                value={amount}
                                onChange={(e) => setAmount(Number(e.target.value))}
                                autoFocus
                            />
                        </label>
                        <div className="modal-actions">
                            <button className="btn btn-ghost" onClick={() => setRestockTarget(null)}>
                                Cancel
                            </button>
                            <button className="btn btn-primary" onClick={submitRestock}>
                                Add stock
                            </button>
                        </div>
                    </div>
                </Modal>
            )}
        </div>
    );
}
