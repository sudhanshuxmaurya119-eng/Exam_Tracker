import seating from "./ai201b-final-seating.json";

export interface FinalAiSeat {
  session: string;
  room: string;
  row: number;
  column: number;
}

export const finalAiSessions = [
  { id: "ai201b-aiml", date: "2026-11-23", shift: "Morning", time: "10:00 AM – 12:00 PM", group: "CSE-AIML" },
  { id: "ai201b-ai", date: "2026-11-23", shift: "Evening", time: "1:30 PM – 3:30 PM", group: "CSE-AI" },
  { id: "ai201b-minor", date: "2026-11-27", shift: "Evening", time: "1:30 PM – 3:30 PM", group: "Minor course" },
];

const assignments: Record<string, FinalAiSeat[]> = seating;

export function getFinalAiSeats(registration: string): FinalAiSeat[] {
  return Object.prototype.hasOwnProperty.call(assignments, registration) ? assignments[registration] : [];
}
