/** Shared TypeScript types mirroring the backend Pydantic schemas. */

export type OrderStatus = "draft" | "confirmed" | "cancelled";
export type InvoiceStatus = "unpaid" | "partially_paid" | "paid" | "cancelled";
export type PaymentMethod = "cash" | "card" | "upi" | "bank_transfer";
export type MovementReason = "purchase" | "sale" | "return" | "adjustment";

export interface User {
    id: number;
    username: string;
    full_name: string | null;
    is_active: boolean;
    is_owner: boolean;
    created_at: string;
}

export interface Product {
    id: number;
    sku: string;
    name: string;
    description: string | null;
    category: string | null;
    unit_price: number;
    cost_price: number;
    quantity_in_stock: number;
    low_stock_threshold: number;
    is_active: boolean;
    is_low_stock: boolean;
    created_at: string;
    updated_at: string;
}

export interface ProductInput {
    sku: string;
    name: string;
    description?: string | null;
    category?: string | null;
    unit_price: number;
    cost_price: number;
    quantity_in_stock: number;
    low_stock_threshold: number;
}

export interface OrderItem {
    id: number;
    product_id: number;
    quantity: number;
    unit_price: number;
    line_total: number;
}

export interface Order {
    id: number;
    reference: string;
    customer_name: string | null;
    customer_phone: string | null;
    status: OrderStatus;
    total_amount: number;
    created_at: string;
    updated_at: string;
    items: OrderItem[];
}

export interface Payment {
    id: number;
    invoice_id: number;
    amount: number;
    method: PaymentMethod;
    reference: string | null;
    paid_at: string;
}

export interface Invoice {
    id: number;
    number: string;
    order_id: number;
    status: InvoiceStatus;
    subtotal: number;
    tax_amount: number;
    total_amount: number;
    amount_paid: number;
    balance_due: number;
    issued_at: string;
    payments: Payment[];
}

export interface LowStockAlert {
    product_id: number;
    sku: string;
    name: string;
    quantity_in_stock: number;
    low_stock_threshold: number;
    deficit: number;
}

export interface DashboardSummary {
    total_products: number;
    active_products: number;
    low_stock_count: number;
    out_of_stock_count: number;
    total_orders: number;
    confirmed_orders: number;
    cancelled_orders: number;
    total_revenue: number;
    outstanding_balance: number;
    inventory_value: number;
}
