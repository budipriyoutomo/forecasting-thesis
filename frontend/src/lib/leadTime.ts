// Batasan thesis (CR v3.5 §5.6): pesanan hasil ROP diasumsikan tiba di periode yang sama,
// yang hanya masuk akal bila lead time < 1 periode (data demand bulanan ≈ 30 hari).
export const LEAD_TIME_PERIOD_DAYS = 30;

export function exceedsOnePeriod(leadTimeDays: number | null | undefined): boolean {
  return typeof leadTimeDays === "number" && leadTimeDays >= LEAD_TIME_PERIOD_DAYS;
}
