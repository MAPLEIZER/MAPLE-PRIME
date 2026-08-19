import { useMemo, useState } from "react";
import type { LegalEntry } from "@/api/knowledge";

export function LegalLibraryPage({ entries, unavailable }: { entries: LegalEntry[]; unavailable: boolean }) {
  const [query, setQuery] = useState("");
  const filtered = useMemo(() => {
    const term = query.trim().toLowerCase();
    if (!term) return entries;
    return entries.filter((entry) =>
      [entry.title, entry.citation, entry.summary, entry.topics.join(" "), entry.provisions.join(" ")]
        .join(" ")
        .toLowerCase()
        .includes(term),
    );
  }, [entries, query]);

  return (
    <section className="space-y-5">
      <div>
        <p className="m-0 text-xs font-semibold uppercase tracking-[0.18em] text-primary">Teaching & reference</p>
        <h2 className="mb-1 mt-2 text-2xl font-semibold">Legal Library</h2>
        <p className="m-0 max-w-3xl text-sm text-muted-foreground">
          Search authoritative Kenyan privacy, digital-credit and cyber-law references. Results identify potentially relevant law; they are not automatic findings or legal advice.
        </p>
      </div>
      <input
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="Search laws, rights, CRB, consent, cybercrime…"
        className="w-full max-w-2xl rounded-lg border border-border bg-card px-4 py-3 text-sm outline-none focus:border-primary"
      />
      {unavailable ? <p className="text-sm text-destructive">Legal library is unavailable.</p> : null}
      <div className="grid gap-4 xl:grid-cols-2">
        {filtered.map((entry) => (
          <article key={entry.id} className="rounded-xl border border-border bg-card p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 className="m-0 text-lg font-semibold">{entry.title}</h3>
                <p className="mb-0 mt-1 text-xs text-muted-foreground">{entry.citation} · source {entry.sourceDate}</p>
              </div>
              <a className="text-sm font-medium text-primary" href={entry.sourceUrl} target="_blank" rel="noreferrer">Official source</a>
            </div>
            <p className="text-sm leading-6 text-muted-foreground">{entry.summary}</p>
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Useful provisions</p>
            <p className="text-sm">{entry.provisions.join(" · ")}</p>
            <p className="rounded-lg bg-muted p-3 text-xs text-muted-foreground">{entry.caution}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
