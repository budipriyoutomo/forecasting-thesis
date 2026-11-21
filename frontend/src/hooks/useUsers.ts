"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { getToken } from "@/lib/auth";
import type { ManagedUser, UserCreateInput, UserUpdateInput } from "@/types/user";

const KEY = ["users"];

// CR v3.7 — daftar user hanya untuk admin; `enabled` false untuk role lain supaya tidak
// memicu 403 (backend tetap penegak akhirnya).
export function useUsers(enabled: boolean) {
  const token = getToken();
  return useQuery<ManagedUser[]>({
    queryKey: KEY,
    enabled: enabled && Boolean(token),
    queryFn: async () => {
      const res = await api.users.list(token as string);
      if (!res.success) throw new Error(res.error.message);
      return res.data;
    },
  });
}

export function useCreateUser() {
  const qc = useQueryClient();
  return useMutation<ManagedUser, Error, UserCreateInput>({
    mutationFn: async (input) => {
      const res = await api.users.create(input, getToken() as string);
      if (!res.success) throw new Error(res.error.message);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useUpdateUser() {
  const qc = useQueryClient();
  return useMutation<ManagedUser, Error, { id: string; input: UserUpdateInput }>({
    mutationFn: async ({ id, input }) => {
      const res = await api.users.update(id, input, getToken() as string);
      if (!res.success) throw new Error(res.error.message);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}
