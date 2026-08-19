import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";

export function PlaceholderPage({ title, description }: { title: string; description: string }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="rounded-lg border border-dashed border-border bg-muted/40 p-6 text-sm text-muted-foreground">Alpha module boundary is established. Data-backed workflows will replace this placeholder without changing the application shell.</div>
      </CardContent>
    </Card>
  );
}
