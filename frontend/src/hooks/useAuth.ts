"use client";

import { useMutation, useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { clearToken, getToken, setToken } from "@/lib/auth";
import type { LoginResponseData, User } from "@/types/auth";

// Login: verifikasi ke backend, simpan token di cookie. Melempar Error dengan
// pesan dari backend supaya form bisa menampilkannya (envelope error, AGENTS.md §4).
export function useLogin() {
  return useMutation<LoginResponseData, Error, { email: string; password: string }>({
    mutationFn: async ({ email, password }) => {
      const res = await api.auth.login(email, password);
      if (!res.success) {
        throw new Error(res.error.message);
      }
      setToken(res.data.access_token);
      return res.data;
    },
  });
}

// Profil user saat ini (GET /me). Query dinonaktifkan kalau belum ada token.
export function useMe() {
  const token = getToken();
  return useQuery<User>({
    queryKey: ["me"],
    enabled: Boolean(token),
    queryFn: async () => {
      const res = await api.auth.me(token as string);
      if (!res.success) {
        throw new Error(res.error.message);
      }
      return res.data;
    },
  });
}

export function logout() {
  clearToken();
}
