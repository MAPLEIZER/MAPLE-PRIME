import type { HTMLAttributes, PropsWithChildren } from "react";

function join(base: string, className?: string): string {
  return className ? `${base} ${className}` : base;
}

export function Card({ className, ...props }: HTMLAttributes<HTMLElement>) {
  return <section className={join("rounded-xl border border-border bg-card text-card-foreground shadow-sm", className)} {...props} />;
}

export function CardHeader({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={join("flex flex-col gap-1.5 p-5", className)} {...props} />;
}

export function CardTitle({ children }: PropsWithChildren) {
  return <h2 className="m-0 text-base font-semibold tracking-tight">{children}</h2>;
}

export function CardDescription({ children }: PropsWithChildren) {
  return <p className="m-0 text-sm text-muted-foreground">{children}</p>;
}

export function CardContent({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={join("px-5 pb-5", className)} {...props} />;
}
