import seating from "./ai201b-final-seating.json";
import cloudSeating from "./ai103e-seating.json";

export interface FinalAiSeat {
  session: string;
  room: string;
  row?: number;
  column?: number;
}

export const finalAiSessions = [
  { id: "ai201b-aiml", subject: "AI201B · Machine Learning Essentials", date: "2026-11-23", shift: "Morning", time: "10:00 AM – 12:00 PM", group: "CSE-AIML" },
  { id: "ai201b-ai", subject: "AI201B · Machine Learning Essentials", date: "2026-11-23", shift: "Evening", time: "1:30 PM – 3:30 PM", group: "CSE-AI" },
  { id: "ai201b-minor", subject: "AI201B · Machine Learning Essentials", date: "2026-11-27", shift: "Evening", time: "1:30 PM – 3:30 PM", group: "Minor course" },
  { id: "ai103e-ai", subject: "AI103E · Cloud Foundations", date: "2026-11-26", shift: "Morning", time: "10:00 AM – 12:00 PM", group: "CSE-AI" },
  { id: "ai103e-aiml", subject: "AI103E · Cloud Foundations", date: "2026-11-26", shift: "Evening", time: "1:30 PM – 3:30 PM", group: "CSE-AIML" },
];

const assignments: Record<string, FinalAiSeat[]> = seating;
const cloudAssignments: Record<string, FinalAiSeat[]> = cloudSeating;

export function getFinalAiSeats(registration: string): FinalAiSeat[] {
  const machineLearning = Object.prototype.hasOwnProperty.call(assignments, registration) ? assignments[registration] : [];
  const cloud = Object.prototype.hasOwnProperty.call(cloudAssignments, registration) ? cloudAssignments[registration] : [];
  return [...machineLearning, ...cloud];
}
