interface LoadingStateProps {
  title: string;
  message: string;
}

export function LoadingState({ title, message }: LoadingStateProps) {
  return (
    <section className="panel">
      <h2>{title}</h2>
      <p className="muted">{message}</p>
    </section>
  );
}