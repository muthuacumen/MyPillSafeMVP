import { applyContractErrorGuard } from '@/lib/trayContractGuard';
import { TraySlotCard } from './TraySlotCard';
import type { TraySlot } from '@/types';

interface TraySlotGridProps {
  slots: TraySlot[];
}

/** Six patient-facing slots, always -- the backend guarantees `slots.length
 * === 6` on every response shape (`tray_messages.py::empty_slots` pads a
 * short reply), so this component does not defend against a short array; it
 * defends against a WRONG one (D-7 defense-in-depth) by running every slot
 * through `applyContractErrorGuard` before render. */
export function TraySlotGrid({ slots }: TraySlotGridProps) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
      {slots.map((slot) => (
        <TraySlotCard key={slot.slot} slot={applyContractErrorGuard(slot)} />
      ))}
    </div>
  );
}
