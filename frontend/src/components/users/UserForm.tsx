"use client";

import { useId, useState, type FormEvent } from "react";

import { FormError } from "@/components/common/FormError";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ROLES } from "@/lib/roles";
import type { Role } from "@/types/auth";
import type { UserCreateInput } from "@/types/user";

// Form tambah user (CR v3.7). Hanya profil + role — password dibuat di Supabase Auth.
export function UserForm({
  onSubmit,
  submitting,
  error,
}: {
  onSubmit: (input: UserCreateInput) => void;
  submitting?: boolean;
  error?: string | null;
}) {
  const id = useId();
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [role, setRole] = useState<Role>("viewer");
  const [invalid, setInvalid] = useState<string | null>(null);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!/^\S+@\S+\.\S+$/.test(email.trim())) return setInvalid("Email tidak valid.");
    if (!name.trim()) return setInvalid("Nama wajib diisi.");
    setInvalid(null);
    onSubmit({ email: email.trim(), name: name.trim(), role });
  };

  return (
    <form onSubmit={submit} className="flex flex-col gap-4" noValidate>
      <div className="flex flex-col gap-2">
        <Label htmlFor={`${id}-email`}>Email</Label>
        <Input id={`${id}-email`} type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        <p className="text-xs text-muted-foreground">Sama persis dengan email akun login di Supabase Auth.</p>
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor={`${id}-name`}>Nama</Label>
        <Input id={`${id}-name`} value={name} onChange={(e) => setName(e.target.value)} />
      </div>
      <div className="flex flex-col gap-2">
        <Label htmlFor={`${id}-role`}>Role</Label>
        <select
          id={`${id}-role`}
          className="h-9 rounded-md border bg-transparent px-3 text-sm"
          value={role}
          onChange={(e) => setRole(e.target.value as Role)}
        >
          {ROLES.map((r) => (
            <option key={r.value} value={r.value}>
              {r.label}
            </option>
          ))}
        </select>
        <p className="text-xs text-muted-foreground">{ROLES.find((r) => r.value === role)?.description}</p>
      </div>
      <FormError message={invalid ?? error} />
      <Button type="submit" disabled={submitting}>
        {submitting ? "Menyimpan…" : "Simpan"}
      </Button>
    </form>
  );
}
