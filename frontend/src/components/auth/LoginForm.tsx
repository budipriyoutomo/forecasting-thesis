"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { useLogin } from "@/hooks/useAuth";

const schema = z.object({
  email: z.string().email("Format email tidak valid"),
  password: z.string().min(1, "Password wajib diisi"),
});

type FormValues = z.infer<typeof schema>;

export function LoginForm() {
  const router = useRouter();
  const login = useLogin();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const onSubmit = handleSubmit((values) => {
    login.mutate(values, {
      onSuccess: () => router.push("/dashboard"),
    });
  });

  return (
    <form onSubmit={onSubmit} className="flex w-full max-w-sm flex-col gap-4" noValidate>
      <div className="flex flex-col gap-1">
        <label htmlFor="email" className="text-sm font-medium">
          Email
        </label>
        <input
          id="email"
          type="email"
          autoComplete="email"
          className="h-10 rounded-md border border-input bg-background px-3 text-sm"
          {...register("email")}
        />
        {errors.email && <p className="text-sm text-destructive">{errors.email.message}</p>}
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="password" className="text-sm font-medium">
          Password
        </label>
        <input
          id="password"
          type="password"
          autoComplete="current-password"
          className="h-10 rounded-md border border-input bg-background px-3 text-sm"
          {...register("password")}
        />
        {errors.password && <p className="text-sm text-destructive">{errors.password.message}</p>}
      </div>

      {login.isError && <p className="text-sm text-destructive">{login.error.message}</p>}

      <Button type="submit" disabled={login.isPending}>
        {login.isPending ? "Masuk…" : "Masuk"}
      </Button>
    </form>
  );
}
