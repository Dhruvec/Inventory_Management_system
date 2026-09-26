import { useEffect, useState } from "react";
import { api } from "../api";
import Modal from "../components/Modal";
import type { Invoice, Order, PaymentMethod } from "../types";
import { currency, dateTime, label } from "../utils/format";

const STATUS_FILTERS = ["", "draft", "confirmed", "cancelled"] as const;

/** Order history with confirm/cancel actions and invoice payment. */
export default function Orders() {
    const [orders, setOrders] = useState<Order[]>([]);
    const [filter, setFilter] = useState<string>("");
    const [error, setError] = useState<string | null>(null);

    const [payOrder, setPayOrder] = useState<Order | null>(null);
    const [invoice, setInvoice] = useState<Invoice | null>(null);
    const [amount, setAmount] = useState(0);
    const [method, setMethod] = useState<PaymentMethod>("cash");

    const load = () =>
        api
            .listOrders(filter || undefined)
            .then(setOrders)
            .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"));

    useEffect(() => {
        load();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [filter]);

    const confirmOrder = async (o: Order) => {
        try {
            await api.confirmOrder(o.id);
            load();
        } catch (e) {
            setError(e instanceof Error ? e.message : "Confirm failed");
        }
    };

    const cancelOrder = async (o: Order) => {
        if (!confirm(`Cancel ${o.reference}? Confirmed orders will restock their items.`)) return;
        try {
            await api.cancelOrder(o.id);
            load();
        } catch (e) {
            setError(e instanceof Error ? e.message : "Cancel failed");
        }
    };

    const openPayment = async (o: Order) => {
        setError(null);
        try {
            const inv = await api.getInvoiceByOrder(o.id);
            setInvoice(inv);
            setAmount(inv.balance_due);
            setPayOrder(o);
        } catch (e) {
            setError(e instanceof Error ? e.message : "No invoice for this order");
        }
    };

    const submitPayment = async () => {
        if (!invoice || amount <= 0) return;
        try {
            await api.addPayment(invoice.id, amount, method);
            setPayOrder(null);
            setInvoice(null);
            load();
        } catch (e) {
            setError(e instanceof Error ? e.message : "Payment failed");
        }
    };

    return (
        <div className="page">
            <header className="page-header">
                <div>
                    <h2>Orders</h2>
                    <p className="muted">Every sale, its status and payment state.</p>
                </div>
                <select className="input" value={filter} onChange={(e) => setFilter(e.target.value)}>
                    {STATUS_FILTERS.map((s) => (
                        <option key={s || "all"} value={s}>
                            {s ? label(s) : "All statuses"}
                        </option>
                    ))}
                </select>
            </header>

            {error && <div className="alert-error">{error}</div>}

            <section className="card">
                {orders.length === 0 ? (
                    <p className="muted empty-state">No orders yet.</p>
                ) : (
                    <table className="table">
                        <thead>
                            <tr>
                                <th>Reference</th>
                                <th>Customer</th>
                                <th className="num">Items</th>
                                <th className="num">Total</th>
                                <th>Status</th>
                                <th>Placed</th>
                                <th />
                            </tr>
                        </thead>
                        <tbody>
                            {orders.map((o) => (
                                <tr key={o.id}>
                                    <td className="mono">{o.reference}</td>
                                    <td>{o.customer_name || "Walk-in"}</td>
                                    <td className="num">{o.items.length}</td>
                                    <td className="num">{currency(o.total_amount)}</td>
                                    <td>
                                        <span className={`badge badge-${o.status}`}>{label(o.status)}</span>
                                    </td>
                                    <td className="muted">{dateTime(o.created_at)}</td>
                                    <td className="num actions">
                                        {o.status === "draft" && (
                                            <button className="btn btn-small" onClick={() => confirmOrder(o)}>
                                                Confirm
                                            </button>
                                        )}
                                        {o.status === "confirmed" && (
                                            <button className="btn btn-small" onClick={() => openPayment(o)}>
                                                Payment
                                            </button>
                                        )}
                                        {o.status !== "cancelled" && (
                                            <button className="btn btn-small btn-danger" onClick={() => cancelOrder(o)}>
                                                Cancel
                                            </button>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </section>

            {payOrder && invoice && (
                <Modal title={`Payment · ${payOrder.reference}`} onClose={() => setPayOrder(null)}>
                    <p className="muted">
                        Invoice {invoice.number} · Total {currency(invoice.total_amount)} · Paid{" "}
                        {currency(invoice.amount_paid)} · Balance{" "}
                        <strong>{currency(invoice.balance_due)}</strong>
                    </p>
                    <div className="form grid-2">
                        <label className="field">
                            <span>Amount</span>
                            <input
                                type="number"
                                min={0}
                                max={invoice.balance_due}
                                value={amount}
                                onChange={(e) => setAmount(Number(e.target.value))}
                                autoFocus
                            />
                        </label>
                        <label className="field">
                            <span>Method</span>
                            <select value={method} onChange={(e) => setMethod(e.target.value as PaymentMethod)}>
                                <option value="cash">Cash</option>
                                <option value="card">Card</option>
                                <option value="upi">UPI</option>
                                <option value="bank_transfer">Bank transfer</option>
                            </select>
                        </label>
                    </div>
                    <div className="modal-actions">
                        <button className="btn btn-ghost" onClick={() => setPayOrder(null)}>
                            Cancel
                        </button>
                        <button className="btn btn-primary" onClick={submitPayment}>
                            Record payment
                        </button>
                    </div>
                </Modal>
            )}
        </div>
    );
}
