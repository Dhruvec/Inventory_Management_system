interface StatCardProps {
    label: string;
    value: string | number;
    hint?: string;
    tone?: "default" | "warn" | "danger" | "good";
}

/** Small KPI tile used on the dashboard. */
export default function StatCard({ label, value, hint, tone = "default" }: StatCardProps) {
    return (
        <div className={`stat-card tone-${tone}`}>
            <div className="stat-label">{label}</div>
            <div className="stat-value">{value}</div>
            {hint && <div className="stat-hint">{hint}</div>}
        </div>
    );
}
