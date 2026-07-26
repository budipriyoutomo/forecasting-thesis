"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { getToken } from "@/lib/auth";
import type { Product, ProductInput } from "@/types/product";

const KEY = ["products"];

export function useProducts() {
  const token = getToken();
  return useQuery<Product[]>({
    queryKey: KEY,
    enabled: Boolean(token),
    queryFn: async () => {
      const res = await api.products.list(token as string);
      if (!res.success) throw new Error(res.error.message);
      return res.data;
    },
  });
}

export function useCreateProduct() {
  const qc = useQueryClient();
  return useMutation<Product, Error, ProductInput>({
    mutationFn: async (input) => {
      const res = await api.products.create(input, getToken() as string);
      if (!res.success) throw new Error(res.error.message);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useUpdateProduct() {
  const qc = useQueryClient();
  return useMutation<Product, Error, { id: string; input: Partial<ProductInput> }>({
    mutationFn: async ({ id, input }) => {
      const res = await api.products.update(id, input, getToken() as string);
      if (!res.success) throw new Error(res.error.message);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useDeleteProduct() {
  const qc = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: async (id) => {
      const res = await api.products.remove(id, getToken() as string);
      if (!res.success) throw new Error(res.error.message);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}
