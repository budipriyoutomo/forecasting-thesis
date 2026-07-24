import { LoginForm } from "@/components/auth/LoginForm";

export default function LoginPage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 px-4">
      <div className="flex flex-col items-center gap-1">
        <h1 className="text-2xl font-semibold">ForecastIQ</h1>
        <p className="text-sm text-muted-foreground">Masuk untuk melanjutkan</p>
      </div>
      <LoginForm />
    </main>
  );
}
