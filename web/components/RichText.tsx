// Renders *bold* markdown segments from pundit text.
export function RichText({ text }: { text: string }) {
  const parts = text.split(/\*(.+?)\*/g);
  return <>{parts.map((p, i) => (i % 2 ? <b key={i}>{p}</b> : <span key={i}>{p}</span>))}</>;
}

export function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h2 className="text-xs uppercase tracking-[0.08em] text-muted mt-6 mb-3 px-1">{children}</h2>;
}

export function Empty({ icon, title, sub }: { icon: string; title: string; sub?: string }) {
  return (
    <div className="text-center text-muted py-11 leading-relaxed">
      <div className="text-4xl mb-2">{icon}</div>
      <div>{title}</div>
      {sub && <div className="text-[13px]">{sub}</div>}
    </div>
  );
}
