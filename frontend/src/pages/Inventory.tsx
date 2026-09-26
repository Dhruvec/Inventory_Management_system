import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import Modal from "../components/Modal";
import type { Product, ProductInput } from "../types";
import { currency } from "../utils/format";

const EMPTY_FORM: ProductInput = {
    sku: "",
    name: "",
    category: "",
    unit_price: 0,
    cost_price: 0,
    quantity_in_stock: 0,
    low_stock_threshold: 10,
};

/** Inventory management: search, create/edit products, adjust stock. */
export default function Inventory() {
    const [products, setProducts] = useState<Product[]>([]);
    const [search, setSearch] = useState("");
    const [lowOnly, setLowOnly] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);

    const [editing, setEditing] = useState<Product | null>(null);
    const [showForm, setShowForm] = useState(false);
    const [form, setForm] = useState<ProductInput>(EMPTY_FORM);
    const [formError, setFormError] = useState<string | null>(null);

    const [stockProduct, setStockProduct] = useState<Product | null>(null);
    const [stockChange, setStockChange] = useState(0);

    const load = useCallback(() => {
        setLoading(true);
        api
            .listProducts({ search, low_stock_only: lowOnly })
            .then(setProducts)
            .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"))
            .finally(() => setLoading(false));
    }, [search, lowOnly]);

    useEffect(() => {
        const t = setTimeout(load, 250); // debounce search
        return () => clearTimeout(t);
    }, [load]);

    const openCreate = () => {
        setEditing(null);
        setForm(EMPTY_FORM);
        setFormError(null);
        setShowForm(true);
    };

    const openEdit = (p: Product) => {
        setEditing(p);
        setForm({
            sku: p.sku,
            name: p.name,
            category: p.category ?? "",
            unit_price: p.unit_price,
            cost_price: p.cost_price,
            quantity_in_stock: p.quantity_in_stock,
            low_stock_threshold: p.low_stock_threshold,
        });
        setFormError(null);
        setShowForm(true);
    };

    const saveProduct = async () => {
        setFormError(null);
        try {
            if (editing) {
                await api.updateProduct(editing.id, form);
            } else {
                await api.createProduct(form);
            }
            setShowForm(false);
            load();
        } catch (e) {
            setFormError(e instanceof Error ? e.message : "Save failed");
        }
    };

    const removeProduct = async (p: Product) => {
        if (!confirm(`Deactivate ${p.name}? Historical records are kept.`)) return;
        try {
            await api.deleteProduct(p.id);
            load();
        } catch (e) {
            setError(e instanceof Error ? e.message : "Delete failed");
        }
    };

    const applyStock = async () => {
        if (!stockProduct || stockChange === 0) return;
        try {
            await api.adjustStock(stockProduct.id, stockChange, "adjustment");
            setStockProduct(null);
            setStockChange(0);
            load();
        } catch (e) {
            setError(e instanceof Error ? e.message : "Stock update failed");
        }
    };

    const set = (k: keyof ProductInput, v: string | number) =>
        setForm((f) => ({ ...f, [k]: v }));

    return (
        <div className="page">
            <header className="page-header">
                <div>
                    <h2>Inventory</h2>
                    <p className="muted">Manage products, pricing and stock levels.</p>
                </div>
                <button className="btn btn-primary" onClick={openCreate}>
                    + Add product
                </button>
            </header>

            <div className="toolbar">
                <input
                    className="input"
                    placeholder="Search by name or SKU…"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                />
                <label className="checkbox">
                    <input
                        type="checkbox"
                        checked={lowOnly}
                        onChange={(e) => setLowOnly(e.target.checked)}
                    />
                    Low stock only
                </label>
            </div>

            {error && <div className="alert-error">{error}</div>}

            <section className="card">
                {loading ? (
                    <p className="muted empty-state">Loading…</p>
                ) : products.length === 0 ? (
                    <p className="muted empty-state">No products found.</p>
                ) : (
                    <table className="table">
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>SKU</th>
                                <th>Category</th>
                                <th className="num">Price</th>
                                <th className="num">Stock</th>
                                <th>Status</th>
                                <th />
                            </tr>
                        </thead>
                        <tbody>
                            {products.map((p) => (
                                <tr key={p.id} className={p.is_low_stock ? "row-warn" : undefined}>
                                    <td>{p.name}</td>
                                    <td className="mono">{p.sku}</td>
                                    <td>{p.category || "—"}</td>
                                    <td className="num">{currency(p.unit_price)}</td>
                                    <td className="num">
                                        {p.quantity_in_stock}
                                        <span className="muted"> / {p.low_stock_threshold}</span>
                                    </td>
                                    <td>
                                        {!p.is_active ? (
                                            <span className="badge badge-muted">Inactive</span>
                                        ) : p.is_low_stock ? (
                                            <span className="badge badge-warn">Low</span>
                                        ) : (
                                            <span className="badge badge-good">OK</span>
                                        )}
                                    </td>
                                    <td className="num actions">
                                        <button className="btn btn-small" onClick={() => openEdit(p)}>
                                            Edit
                                        </button>
                                        <button
                                            className="btn btn-small"
                                            onClick={() => {
                                                setStockProduct(p);
                                                setStockChange(0);
                                            }}
                                        >
                                            Stock
                                        </button>
                                        <button className="btn btn-small btn-danger" onClick={() => removeProduct(p)}>
                                            Delete
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </section>

            {showForm && (
                <Modal
                    title={editing ? `Edit: ${editing.name}` : "Add product"}
                    onClose={() => setShowForm(false)}
                >
                    <div className="form grid-2">
                        <label className="field">
                            <span>SKU</span>
                            <input
                                value={form.sku}
                                disabled={!!editing}
                                onChange={(e) => set("sku", e.target.value)}
                            />
                        </label>
                        <label className="field">
                            <span>Name</span>
                            <input value={form.name} onChange={(e) => set("name", e.target.value)} />
                        </label>
                        <label className="field">
                            <span>Category</span>
                            <input
                                value={form.category ?? ""}
                                onChange={(e) => set("category", e.target.value)}
                            />
                        </label>
                        <label className="field">
                            <span>Selling price</span>
                            <input
                                type="number"
                                min={0}
                                value={form.unit_price}
                                onChange={(e) => set("unit_price", Number(e.target.value))}
                            />
                        </label>
                        <label className="field">
                            <span>Cost price</span>
                            <input
                                type="number"
                                min={0}
                                value={form.cost_price}
                                onChange={(e) => set("cost_price", Number(e.target.value))}
                            />
                        </label>
                        {!editing && (
                            <label className="field">
                                <span>Opening stock</span>
                                <input
                                    type="number"
                                    min={0}
                                    value={form.quantity_in_stock}
                                    onChange={(e) => set("quantity_in_stock", Number(e.target.value))}
                                />
                            </label>
                        )}
                        <label className="field">
                            <span>Low-stock threshold</span>
                            <input
                                type="number"
                                min={0}
                                value={form.low_stock_threshold}
                                onChange={(e) => set("low_stock_threshold", Number(e.target.value))}
                            />
                        </label>
                    </div>

                    {formError && <div className="alert-error">{formError}</div>}

                    <div className="modal-actions">
                        <button className="btn btn-ghost" onClick={() => setShowForm(false)}>
                            Cancel
                        </button>
                        <button className="btn btn-primary" onClick={saveProduct}>
                            {editing ? "Save changes" : "Create product"}
                        </button>
                    </div>
                </Modal>
            )}

            {stockProduct && (
                <Modal
                    title={`Adjust stock: ${stockProduct.name}`}
                    onClose={() => setStockProduct(null)}
                >
                    <p className="muted">
                        Current stock: <strong>{stockProduct.quantity_in_stock}</strong>. Use a negative
                        number to remove stock (e.g. damage), positive to add.
                    </p>
                    <div className="form">
                        <label className="field">
                            <span>Change</span>
                            <input
                                type="number"
                                value={stockChange}
                                onChange={(e) => setStockChange(Number(e.target.value))}
                                autoFocus
                            />
                        </label>
                        <div className="modal-actions">
                            <button className="btn btn-ghost" onClick={() => setStockProduct(null)}>
                                Cancel
                            </button>
                            <button className="btn btn-primary" onClick={applyStock}>
                                Apply
                            </button>
                        </div>
                    </div>
                </Modal>
            )}
        </div>
    );
}
