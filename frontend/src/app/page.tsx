import { BackendStatus } from "@/components/dashboard/BackendStatus";

export default function HomePage() {
  return (
    <main className="container flex min-h-screen flex-col justify-center gap-3 py-16">
      <h1 className="text-2xl font-semibold">ForecastIQ</h1>
      <p className="text-muted-foreground">
        Forecasting raw material &amp; inventory untuk tim PPIC — scaffold Fase 0.
      </p>
      <BackendStatus />
    </main>
  );
}
