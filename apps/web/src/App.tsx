import { AlertTriangle, Building2, Database, FileCheck2, Scale, Send } from "lucide-react";

type CardProps = { label: string; value: string; note: string };

function MetricCard({ label, value, note }: CardProps) {
  return (
    <article className="card metric">
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{note}</small>
    </article>
  );
}

export function App() {
  return (
    <div className="shell">
      <aside>
        <div className="brand"><span>KDR</span><div>Kenya Data Rights<small>Local-first privacy control</small></div></div>
        <nav>
          <a className="active"><Database size={17}/> Overview</a>
          <a><Building2 size={17}/> Institutions</a>
          <a><FileCheck2 size={17}/> My requests</a>
          <a><Scale size={17}/> Cases</a>
          <a><Send size={17}/> Reports</a>
        </nav>
        <div className="local-badge">Local mode · no telemetry</div>
      </aside>
      <main>
        <header>
          <div><p className="eyebrow">REGULATORY INTELLIGENCE</p><h1>Overview</h1></div>
          <button>Sync sources</button>
        </header>
        <section className="metrics">
          <MetricCard label="CBK DCP reference" value="252" note="9 Jul 2026 source snapshot" />
          <MetricCard label="ODPC reconciliation" value="Pending" note="No compliance inference yet" />
          <MetricCard label="Open requests" value="0" note="Targeted requests only" />
          <MetricCard label="Manual review" value="0" note="Fuzzy matches and legal outcomes" />
        </section>
        <section className="grid">
          <article className="card panel">
            <div className="panel-title"><div><p className="eyebrow">SOURCE COVERAGE</p><h2>Regulatory layers</h2></div></div>
            {[['CBK','Licensing and official DCP contacts','Ready'],['ODPC','Controller / processor observations','Importer pending'],['CRB','Regulatory status + user evidence','Designed'],['Kenya Law','Appeals and statutory context','Designed']].map(([name,desc,status]) => (
              <div className="row" key={name}><div><b>{name}</b><span>{desc}</span></div><em>{status}</em></div>
            ))}
          </article>
          <article className="card panel attention">
            <div className="panel-title"><AlertTriangle size={19}/><div><p className="eyebrow">ATTENTION</p><h2>Review queue</h2></div></div>
            <div className="notice"><b>No automatic accusations</b><span>Unmatched regulator records remain evidence gaps until manually resolved.</span></div>
            <div className="notice"><b>CRB evidence boundary</b><span>Public registry status is separate from proof that a lender submitted your data.</span></div>
          </article>
        </section>
        <section className="card table-card">
          <div className="panel-title"><div><p className="eyebrow">MY RIGHTS</p><h2>Request workflow</h2></div><button className="secondary">New request</button></div>
          <div className="empty"><FileCheck2 size={30}/><b>No requests yet</b><span>Create a targeted access, correction, erasure, objection or CRB-dispute request.</span></div>
        </section>
      </main>
    </div>
  );
}
