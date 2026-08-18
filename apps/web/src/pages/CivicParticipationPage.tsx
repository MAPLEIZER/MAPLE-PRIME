import { useState } from "react";
import type { CivicCandidate, CivicDraftResult, Consultation } from "@/api/knowledge";
import { Button } from "@/components/ui/Button";

interface Props {
  consultations: Consultation[];
  unavailable: boolean;
  candidates?: CivicCandidate[];
  discovering?: boolean;
  onDiscover?: () => Promise<void>;
  onDraft?: (consultationId: string, input: { submitterName: string; position: string; points: string[] }) => Promise<CivicDraftResult>;
}

export function CivicParticipationPage({
  consultations,
  unavailable,
  candidates = [],
  discovering = false,
  onDiscover,
  onDraft,
}: Props) {
  const [name, setName] = useState("");
  const [points, setPoints] = useState("");
  const [result, setResult] = useState<CivicDraftResult | null>(null);
  const [working, setWorking] = useState<string | null>(null);

  async function createDraft(item: Consultation) {
    if (!onDraft || !name.trim() || !points.trim()) return;
    setWorking(item.id);
    try {
      setResult(await onDraft(item.id, {
        submitterName: name.trim(),
        position: "comment",
        points: points.split("\n").map((value) => value.trim()).filter(Boolean).slice(0, 12),
      }));
    } finally {
      setWorking(null);
    }
  }

  return (
    <section className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="m-0 text-xs font-semibold uppercase tracking-[0.18em] text-primary">Individual civic participation</p>
          <h2 className="mb-1 mt-2 text-2xl font-semibold">Civic Participation</h2>
          <p className="m-0 max-w-3xl text-sm text-muted-foreground">
            Find official consultations affecting AI, cybersecurity and data privacy. KDR may draft one memorandum from your points, but will never bulk-submit, fabricate identities or silently send it.
          </p>
        </div>
        <Button disabled={!onDiscover || discovering} onClick={() => void onDiscover?.()}>
          {discovering ? "Checking official sites…" : "Discover official consultations"}
        </Button>
      </div>

      {candidates.length > 0 ? (
        <div className="rounded-xl border border-primary/40 bg-card p-5">
          <h3 className="mt-0">Discovery candidates — review required</h3>
          <p className="text-sm text-muted-foreground">These links were found on allowlisted official sites. KDR has not added them as an open consultation or submitted anything.</p>
          <div className="space-y-2">
            {candidates.map((candidate) => (
              <div key={`${candidate.sourceId}:${candidate.url}`} className="rounded-lg bg-muted p-3">
                <a className="font-medium text-primary" href={candidate.url} target="_blank" rel="noreferrer">{candidate.title}</a>
                <p className="mb-0 mt-1 text-xs text-muted-foreground">{candidate.agency}</p>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      <div className="grid gap-3 rounded-xl border border-border bg-card p-5 md:grid-cols-2">
        <label className="grid gap-1 text-sm">Your name<input className="rounded-md border border-border bg-background px-3 py-2" value={name} onChange={(e) => setName(e.target.value)} /></label>
        <label className="grid gap-1 text-sm md:col-span-2">Your points — one per line<textarea className="min-h-28 rounded-md border border-border bg-background px-3 py-2" value={points} onChange={(e) => setPoints(e.target.value)} placeholder="Require privacy-by-design…\nRequire independent security testing…" /></label>
      </div>
      {unavailable ? <p className="text-sm text-destructive">Consultation registry is unavailable.</p> : null}
      <div className="space-y-4">
        {consultations.map((item) => (
          <article key={item.id} className="rounded-xl border border-border bg-card p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 className="m-0 text-lg font-semibold">{item.title}</h3>
                <p className="mb-0 mt-1 text-sm text-muted-foreground">{item.agency}</p>
              </div>
              <span className="rounded-full bg-muted px-3 py-1 text-xs font-semibold uppercase">{item.status}</span>
            </div>
            <p className="text-sm text-muted-foreground">Deadline: {new Date(item.deadline).toLocaleString()}</p>
            <div className="flex flex-wrap gap-2">
              <a className="text-sm font-medium text-primary" href={item.sourceUrl} target="_blank" rel="noreferrer">Official notice</a>
              {item.channels.filter((channel) => channel.kind === "form" && channel.url).map((channel) => (
                <a key={channel.label} className="text-sm font-medium text-primary" href={channel.url ?? undefined} target="_blank" rel="noreferrer">{channel.label}</a>
              ))}
            </div>
            {item.status === "open" ? (
              <Button className="mt-4" disabled={!onDraft || working === item.id || !name.trim() || !points.trim()} onClick={() => void createDraft(item)}>
                {working === item.id ? "Drafting…" : "Create reviewable memorandum"}
              </Button>
            ) : <p className="mt-4 text-xs text-muted-foreground">Submission actions disabled because this published participation window is closed.</p>}
          </article>
        ))}
      </div>
      {result ? (
        <div className="rounded-xl border border-primary/40 bg-card p-5">
          <h3 className="mt-0">Draft ready for your review</h3>
          <p className="text-sm text-muted-foreground">KDR has not sent anything.</p>
          <pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded-lg bg-muted p-4 text-sm">{result.body}</pre>
          <div className="flex flex-wrap gap-3">
            {result.mailtoLinks.map((link) => <a key={link.url} className="font-medium text-primary" href={link.url}>{link.label}</a>)}
            {result.formLinks.map((link) => <a key={link.url} className="font-medium text-primary" href={link.url} target="_blank" rel="noreferrer">{link.label}</a>)}
          </div>
        </div>
      ) : null}
    </section>
  );
}
