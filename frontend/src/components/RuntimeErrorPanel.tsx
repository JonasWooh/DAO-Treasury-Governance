interface RuntimeErrorPanelProps {
  title: string;
  error: string;
}

export function RuntimeErrorPanel({ title, error }: RuntimeErrorPanelProps) {
  return (
    <section className="panel panel-error">
      <h2>{title}</h2>
      <p>{error}</p>
    </section>
  );
}