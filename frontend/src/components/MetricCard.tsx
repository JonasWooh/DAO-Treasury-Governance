interface MetricCardProps {
  label: string;
  value: string;
  helper?: string;
}

export function MetricCard({ label, value, helper }: MetricCardProps) {
  return (
    <article className="metric-card">
      <span className="metric-label">{label}</span>
      <strong className="metric-value">{value}</strong>
      {helper ? <span className="metric-helper">{helper}</span> : null}
    </article>
  );
}