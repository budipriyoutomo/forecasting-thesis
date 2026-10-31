"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { getToken } from "@/lib/auth";
import type { ForecastSettings, ForecastSettingsInput } from "@/types/forecastSettings";

const KEY = ["forecast-settings"];

export function useForecastSettings() {
  const token = getToken();
  return useQuery<ForecastSettings>({
    queryKey: KEY,
    enabled: Boolean(token),
    queryFn: async () => {
      const res = await api.forecastSettings.get(token as string);
      if (!res.success) throw new Error(res.error.message);
      return res.data;
    },
  });
}

export function useUpdateForecastSettings() {
  const qc = useQueryClient();
  return useMutation<ForecastSettings, Error, ForecastSettingsInput>({
    mutationFn: async (input) => {
      const res = await api.forecastSettings.update(input, getToken() as string);
      if (!res.success) throw new Error(res.error.message);
      return res.data;
    },
    onSuccess: (data) => {
      qc.setQueryData(KEY, data);
      // Daftar MethodSelector ikut berubah bila metode aktif diubah.
      qc.invalidateQueries({ queryKey: ["forecast-methods"] });
    },
  });
}
