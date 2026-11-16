import manifest from "./seating-plans.json";

export interface SuppliedPlan {
  id: string;
  date: string;
  shift: string;
  kind: string;
  url: string;
  pages: number;
  indexUrl?: string;
  seatCount?: number;
  universityBatch?: boolean;
}
interface Room { room: string; building: string; floor: string; page: number }
interface SeatIndex { rooms: Room[]; seats: [string, number, number, number][] }
export interface SuppliedSeat extends Room {
  plan: SuppliedPlan;
  roll: string;
  row: number;
  column: number;
}
export const suppliedPlans: SuppliedPlan[] = manifest;
export const roomwisePlans = suppliedPlans.filter(p => p.kind === "roomwise");
export const assetUrl = (path: string) => `${import.meta.env.BASE_URL}${path}`;
export const planDate = (date: string) => new Date(`${date}T00:00:00`).toLocaleDateString("en-IN", {
  day: "numeric", month: "short", year: "numeric",
});
export const planTime = (shift: string) => shift === "Morning" ? "10:00 AM – 12:00 PM" : "1:30 PM – 3:30 PM";
const indexes = new Map<string, Promise<SeatIndex>>();

async function getIndex(plan: SuppliedPlan): Promise<SeatIndex> {
  let pending = indexes.get(plan.id);
  if (!pending) {
    pending = fetch(assetUrl(plan.indexUrl!)).then(async response => {
      if (!response.ok) throw new Error("Plan unavailable");
      return response.json() as Promise<SeatIndex>;
    }).catch(error => { indexes.delete(plan.id); throw error; });
    indexes.set(plan.id, pending);
  }
  return pending;
}

export async function searchSuppliedSeats(roll: string, planId?: string, shift?: string): Promise<SuppliedSeat[]> {
  const plans = roomwisePlans.filter(p => (!planId || p.id === planId) && (!shift || p.shift.toLowerCase() === shift.toLowerCase()));
  const results = await Promise.all(plans.map(async plan => {
    const index = await getIndex(plan);
    return index.seats.filter(seat => seat[0] === roll).map(seat => ({
      ...index.rooms[seat[1]], plan, roll, row: seat[2], column: seat[3],
    }));
  }));
  return results.flat();
}
