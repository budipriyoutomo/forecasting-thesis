import { Badge } from "@/components/ui/badge";

// Badge peringatan untuk material yang lead time-nya ≥ 1 periode (CR v3.5 §5.6).
export function LeadTimeWarning({ leadTimeDays }: { leadTimeDays: number }) {
  return (
    <Badge
      variant="outline"
      className="border-amber-500 text-amber-700 dark:text-amber-400"
      title={`Lead time ${leadTimeDays} hari ≥ 1 periode — asumsi pesanan tiba di periode yang sama tidak berlaku.`}
    >
      Lead time ≥ 1 periode
    </Badge>
  );
}
