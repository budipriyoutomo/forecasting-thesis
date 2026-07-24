"use client";

import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { getToken } from "@/lib/auth";
import type { DashboardSummary } from "@/types/dashboard";

export function useDashboardSummary() {
  const token = getToken();
  return useQuery<DashboardSummary>({
    queryKey: ["dashboard-summary"],
    enabled: Boolean(token),
    queryFn: async () => {
      const res = await api.dashboard.summary(token as string);
      if (!res.success) throw new Error(res.error.message);
      return res.data;
    },
  });
}
