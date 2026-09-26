/**
 * Thin typed wrapper around fetch for talking to the FastAPI backend.
 * Attaches the JWT (if present) and normalises error handling.
 */
import type {
    DashboardSummary,
    Invoice,
    LowStockAlert,
    Order,
    PaymentMethod,
    Product,
    ProductInput,
    User,
} from "./types";

const TOKEN_KEY = "inventory_token";

export function getToken(): string | null {
    return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
    status: number;
    constructor(status: number, message: string) {
        super(message);
        this.status = status;
    }
}

async function request<T>(
    path: string,
    options: RequestInit = {},
): Promise<T> {
    const headers: Record<string, string> = {
        ...(options.headers as Record<string, string>),
    };
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
    if (options.body && !headers["Content-Type"]) {
        headers["Content-Type"] = "application/json";
    }

    const res = await fetch(`/api${path}`, { ...options, headers });
    if (res.status === 204) return undefined as T;

    const text = await res.text();
    const data = text ? JSON.parse(text) : null;
    if (!res.ok) {
        const detail =
            (data && (data.detail || data.message)) || `Request failed (${res.status})`;
        throw new ApiError(res.status, typeof detail === "string" ? detail : "Error");
    }
    return data as T;
}

export const api = {
    // --- Auth ---------------------------------------------------------------
    async login(username: string, password: string): Promise<string> {
        const body = new URLSearchParams({ username, password });
        const res = await fetch("/api/auth/token", {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body,
        });
        if (!res.ok) throw new ApiError(res.status, "Invalid username or password");
        const data = await res.json();
        setToken(data.access_token);
        return data.access_token as string;
    },
    async register(payload: {
        username: string;
        password: string;
        full_name?: string;
    }): Promise<User> {
        return request<User>("/auth/register", {
            method: "POST",
            body: JSON.stringify(payload),
        });
    },
    me: () => request<User>("/auth/me"),

    // --- Products -----------------------------------------------------------
    listProducts: (params: { search?: string; low_stock_only?: boolean } = {}) => {
        const qs = new URLSearchParams();
        if (params.search) qs.set("search", params.search);
        if (params.low_stock_only) qs.set("low_stock_only", "true");
        const suffix = qs.toString() ? `?${qs}` : "";
        return request<Product[]>(`/products${suffix}`);
    },
    getProduct: (id: number) => request<Product>(`/products/${id}`),
    createProduct: (payload: ProductInput) =>
        request<Product>("/products", {
            method: "POST",
            body: JSON.stringify(payload),
        }),
    updateProduct: (id: number, payload: Partial<ProductInput>) =>
        request<Product>(`/products/${id}`, {
            method: "PUT",
            body: JSON.stringify(payload),
        }),
    deleteProduct: (id: number) =>
        request<void>(`/products/${id}`, { method: "DELETE" }),
    adjustStock: (id: number, change: number, reason = "adjustment", note?: string) =>
        request<Product>(`/products/${id}/stock`, {
            method: "POST",
            body: JSON.stringify({ change, reason, note }),
        }),

    // --- Orders -------------------------------------------------------------
    listOrders: (status?: string) => {
        const suffix = status ? `?status=${status}` : "";
        return request<Order[]>(`/orders${suffix}`);
    },
    createOrder: (payload: {
        customer_name?: string;
        customer_phone?: string;
        items: { product_id: number; quantity: number }[];
        confirm: boolean;
    }) =>
        request<Order>("/orders", {
            method: "POST",
            body: JSON.stringify(payload),
        }),
    confirmOrder: (id: number) =>
        request<Order>(`/orders/${id}/confirm`, { method: "POST" }),
    cancelOrder: (id: number) =>
        request<Order>(`/orders/${id}/cancel`, { method: "POST" }),

    // --- Invoices -----------------------------------------------------------
    listInvoices: () => request<Invoice[]>("/invoices"),
    getInvoiceByOrder: (orderId: number) =>
        request<Invoice>(`/invoices/by-order/${orderId}`),
    addPayment: (invoiceId: number, amount: number, method: PaymentMethod = "cash") =>
        request<Invoice>(`/invoices/${invoiceId}/payments`, {
            method: "POST",
            body: JSON.stringify({ amount, method }),
        }),

    // --- Alerts & dashboard -------------------------------------------------
    lowStockAlerts: () => request<LowStockAlert[]>("/alerts/low-stock"),
    dashboardSummary: () => request<DashboardSummary>("/dashboard/summary"),
};
