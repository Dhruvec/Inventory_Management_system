import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import type { Product } from "../types";
import { currency } from "../utils/format";

interface CartLine {
    product: Product;
    quantity: number;
}

/** Billing counter: build a cart, take payment, and print a receipt. */
export default function Billing() {
    const [products, setProducts] = useState<Product[]>([]);
    const [search, setSearch] = useState("");
    const [cart, setCart] = useState<CartLine[]>([]);
    const [customerName, setCustomerName] = useState("");
    const [customerPhone, setCustomerPhone] = useState("");
    const [error, setError] = useState<string | null>(null);
    const [status, setStatus] = useState<string | null>(null);
    const [receipt, setReceipt] = useState<string | null>(null);
    const [busy, setBusy] = useState(false);

    useEffect(() => {
        api.listProducts({ search }).then(setProducts).catch(() => undefined);
    }, [search]);

    const cartTotal = useMemo(
        () => cart.reduce((sum, l) => sum + l.product.unit_price * l.quantity, 0),
        [cart],
    );

    const addToCart = (product: Product) => {
        setStatus(null);
        setCart((prev) => {
            const existing = prev.find((l) => l.product.id === product.id);
            if (existing) {
                return prev.map((l) =>
                    l.product.id === product.id ? { ...l, quantity: l.quantity + 1 } : l,
                );
            }
            return [...prev, { product, quantity: 1 }];
        });
    };

    const setQty = (id: number, qty: number) =>
        setCart((prev) =>
            prev
                .map((l) => (l.product.id === id ? { ...l, quantity: Math.max(0, qty) } : l))
                .filter((l) => l.quantity > 0),
        );

    const clearCart = () => {
        setCart([]);
        setCustomerName("");
        setCustomerPhone("");
        setReceipt(null);
        setStatus(null);
    };

    const checkout = async () => {
        setError(null);
        setStatus(null);
        if (cart.length === 0) {
            setError("Cart is empty.");
            return;
        }
        setBusy(true);
        try {
            const order = await api.createOrder({
                customer_name: customerName || undefined,
                customer_phone: customerPhone || undefined,
                items: cart.map((l) => ({ product_id: l.product.id, quantity: l.quantity })),
                confirm: true,
            });
            // Immediately settle the invoice in full (typical counter sale).
            const invoice = await api.getInvoiceByOrder(order.id);
            await api.addPayment(invoice.id, invoice.total_amount, "cash");
            setReceipt(order.reference);
            setStatus(`Sale completed. Order ${order.reference} · ${currency(order.total_amount)}`);
            setCart([]);
            setCustomerName("");
            setCustomerPhone("");
            // Refresh stock levels.
            api.listProducts({ search }).then(setProducts).catch(() => undefined);
        } catch (e) {
            setError(e instanceof Error ? e.message : "Checkout failed");
        } finally {
            setBusy(false);
        }
    };

    return (
        <div className="page billing-layout">
            <section className="billing-products">
                <header className="page-header">
                    <div>
                        <h2>Billing</h2>
                        <p className="muted">Pick items to build the customer's bill.</p>
                    </div>
                </header>
                <input
                    className="input"
                    placeholder="Search products…"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                />
                <div className="product-grid">
                    {products
                        .filter((p) => p.is_active && p.quantity_in_stock > 0)
                        .map((p) => (
                            <button
                                key={p.id}
                                className="product-tile"
                                onClick={() => addToCart(p)}
                                disabled={p.quantity_in_stock === 0}
                            >
                                <div className="product-tile-name">{p.name}</div>
                                <div className="product-tile-meta">
                                    <span>{currency(p.unit_price)}</span>
                                    <span className="muted">{p.quantity_in_stock} left</span>
                                </div>
                            </button>
                        ))}
                    {products.length === 0 && (
                        <p className="muted empty-state">No matching products.</p>
                    )}
                </div>
            </section>

            <aside className="billing-cart card">
                <h3>Current bill</h3>

                <div className="cart-customer">
                    <input
                        className="input"
                        placeholder="Customer name (optional)"
                        value={customerName}
                        onChange={(e) => setCustomerName(e.target.value)}
                    />
                    <input
                        className="input"
                        placeholder="Phone (optional)"
                        value={customerPhone}
                        onChange={(e) => setCustomerPhone(e.target.value)}
                    />
                </div>

                {cart.length === 0 ? (
                    <p className="muted empty-state">No items yet. Tap a product to add it.</p>
                ) : (
                    <table className="table table-compact">
                        <tbody>
                            {cart.map((l) => (
                                <tr key={l.product.id}>
                                    <td>{l.product.name}</td>
                                    <td className="num qty-cell">
                                        <button className="qty-btn" onClick={() => setQty(l.product.id, l.quantity - 1)}>
                                            −
                                        </button>
                                        <span>{l.quantity}</span>
                                        <button className="qty-btn" onClick={() => setQty(l.product.id, l.quantity + 1)}>
                                            +
                                        </button>
                                    </td>
                                    <td className="num">{currency(l.product.unit_price * l.quantity)}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}

                <div className="cart-total">
                    <span>Total</span>
                    <strong>{currency(cartTotal)}</strong>
                </div>

                {error && <div className="alert-error">{error}</div>}
                {status && <div className="alert-success">{status}</div>}
                {receipt && <p className="muted">Receipt for order {receipt} recorded.</p>}

                <div className="modal-actions">
                    <button className="btn btn-ghost" onClick={clearCart} disabled={busy}>
                        Clear
                    </button>
                    <button className="btn btn-primary" onClick={checkout} disabled={busy || cart.length === 0}>
                        {busy ? "Processing…" : `Charge ${currency(cartTotal)}`}
                    </button>
                </div>
            </aside>
        </div>
    );
}
