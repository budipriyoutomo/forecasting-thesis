// Label ramah untuk kode metode engine — dipakai MethodSelector & Pengaturan Forecast.
export const METHOD_LABELS: Record<string, string> = {
  moving_average: "Moving Average",
  exponential_smoothing: "Exponential Smoothing",
  random_forest: "Random Forest",
  xgboost: "XGBoost",
  lstm: "LSTM",
  ets: "ETS (Exponential Smoothing)",
  arima: "ARIMA",
  lgbm: "LightGBM",
  croston: "Croston / SBA",
  prophet: "Prophet",
};

export function methodLabel(code: string): string {
  return METHOD_LABELS[code] ?? code;
}
