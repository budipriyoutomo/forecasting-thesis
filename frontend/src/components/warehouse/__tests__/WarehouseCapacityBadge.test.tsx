import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { WarehouseCapacityBadge } from "@/components/warehouse/WarehouseCapacityBadge";

describe("WarehouseCapacityBadge", () => {
  it("menampilkan 'Muat' saat is_within_capacity true", () => {
    render(
      <WarehouseCapacityBadge
        validation={{
          run_id: "r1",
          total_pallet_capacity: "100",
          total_pallet_required: "2",
          is_within_capacity: true,
        }}
      />,
    );
    expect(screen.getByText(/muat di gudang/i)).toBeDefined();
  });

  it("menampilkan 'Melebihi' saat is_within_capacity false", () => {
    render(
      <WarehouseCapacityBadge
        validation={{
          run_id: "r1",
          total_pallet_capacity: "1",
          total_pallet_required: "3",
          is_within_capacity: false,
        }}
      />,
    );
    expect(screen.getByText(/melebihi kapasitas gudang/i)).toBeDefined();
  });
});
