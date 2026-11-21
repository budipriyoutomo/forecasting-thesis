"use client";

import { Plus } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/common/PageHeader";
import { TableSkeleton } from "@/components/common/TableSkeleton";
import { UserForm } from "@/components/users/UserForm";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useMe } from "@/hooks/useAuth";
import { useCreateUser, useUpdateUser, useUsers } from "@/hooks/useUsers";
import { can } from "@/lib/permissions";
import { ROLES, roleLabel } from "@/lib/roles";
import type { Role } from "@/types/auth";
import type { ManagedUser, UserCreateInput, UserUpdateInput } from "@/types/user";

// Manajemen User (CR v3.7) — admin mendaftarkan profil + role, mengubah role, dan
// menonaktifkan user. Password tetap di Supabase Auth; user tidak dihapus (FK run/override).
export default function UsersPage() {
  const { data: me, isPending: mePending } = useMe();
  const allowed = can(me?.role, "user.manage");
  const users = useUsers(allowed);
  const create = useCreateUser();
  const update = useUpdateUser();
  const [open, setOpen] = useState(false);

  const change = (u: ManagedUser, input: UserUpdateInput, done: string) =>
    update.mutate(
      { id: u.id, input },
      { onSuccess: () => toast.success(done), onError: (e) => toast.error(e.message) },
    );

  const onCreate = (input: UserCreateInput) =>
    create.mutate(input, {
      onSuccess: (u) => {
        setOpen(false);
        toast.success(`${u.name} ditambahkan sebagai ${roleLabel(u.role)}`);
      },
    });

  if (!mePending && !allowed) {
    return (
      <div className="flex flex-col gap-6">
        <PageHeader title="Manajemen User" />
        <Alert>
          <AlertDescription>Halaman ini khusus admin.</AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Manajemen User"
        description="Atur siapa yang bisa masuk dan apa yang boleh dilakukan. Perubahan role atau status berlaku saat user login berikutnya."
        actions={
          allowed && (
            <Button
              onClick={() => {
                create.reset();
                setOpen(true);
              }}
            >
              <Plus />
              Tambah user
            </Button>
          )
        }
      />

      <Alert>
        <AlertDescription>
          Password tidak dikelola di sini. Buat akun login (email + password) di Supabase Auth, lalu daftarkan
          email yang sama di halaman ini beserta role-nya. User tidak bisa dihapus karena riwayat forecast dan
          override menyimpan pelakunya — pakai <em>Nonaktifkan</em> untuk mencabut akses.
        </AlertDescription>
      </Alert>

      {(mePending || users.isPending) && <TableSkeleton columns={5} />}
      {users.isError && (
        <Alert variant="destructive">
          <AlertDescription>Gagal memuat daftar user: {users.error.message}</AlertDescription>
        </Alert>
      )}
      {users.data && (
        <div className="overflow-x-auto rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nama</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Aksi</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {users.data.map((u) => {
                const self = u.id === me?.id;
                return (
                  <TableRow key={u.id} className={u.is_active ? undefined : "text-muted-foreground"}>
                    <TableCell className="whitespace-nowrap font-medium">
                      {u.name} {self && <span className="text-xs text-muted-foreground">(Anda)</span>}
                    </TableCell>
                    <TableCell className="whitespace-nowrap">{u.email}</TableCell>
                    <TableCell>
                      <select
                        aria-label={`Role ${u.name}`}
                        className="h-8 rounded-md border bg-transparent px-2 text-sm disabled:opacity-60"
                        value={u.role}
                        disabled={self || update.isPending}
                        title={self ? "Role akun sendiri tidak bisa diubah" : undefined}
                        onChange={(e) => {
                          const role = e.target.value as Role;
                          change(u, { role }, `Role ${u.name} → ${roleLabel(role)}`);
                        }}
                      >
                        {ROLES.map((r) => (
                          <option key={r.value} value={r.value}>
                            {r.label}
                          </option>
                        ))}
                      </select>
                    </TableCell>
                    <TableCell>
                      <Badge variant={u.is_active ? "secondary" : "outline"}>{u.is_active ? "Aktif" : "Nonaktif"}</Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={self || update.isPending}
                        title={self ? "Akun sendiri tidak bisa dinonaktifkan" : undefined}
                        onClick={() =>
                          change(u, { is_active: !u.is_active }, `${u.name} ${u.is_active ? "dinonaktifkan" : "diaktifkan"}`)
                        }
                      >
                        {u.is_active ? "Nonaktifkan" : "Aktifkan"}
                      </Button>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      )}

      <div className="grid gap-2 text-sm sm:grid-cols-2">
        {ROLES.map((r) => (
          <div key={r.value} className="rounded-lg border p-3">
            <p className="font-medium">{r.label}</p>
            <p className="text-muted-foreground">{r.description}</p>
          </div>
        ))}
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Tambah user</DialogTitle>
            <DialogDescription>
              Pastikan akun login dengan email yang sama sudah dibuat di Supabase Auth.
            </DialogDescription>
          </DialogHeader>
          <UserForm onSubmit={onCreate} submitting={create.isPending} error={create.error?.message} />
        </DialogContent>
      </Dialog>
    </div>
  );
}
