import { getTierName, scorePct, tierBadgeClass, tierBadgeLabel } from "@/lib/format";

export default function TierBadge({ probability }: { probability: number }) {
  const tier = getTierName(probability);
  return (
    <span className={tierBadgeClass(tier)}>
      {tierBadgeLabel(tier)} ({scorePct(probability)}%)
    </span>
  );
}
