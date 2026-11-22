import React from "react";
import { finalAiSessions, FinalAiSeat } from "../data/finalAiSeating";
import { planDate } from "../data/suppliedSeating";

export const FinalAiResults: React.FC<{ seats: FinalAiSeat[] }> = ({ seats }) => (
  <section aria-live="polite" className="space-y-3">
    <h2 className="text-xl font-bold">AI201B · Machine Learning Essentials</h2>
    {seats.map(seat => {
      const session = finalAiSessions.find(item => item.id === seat.session)!;
      return (
        <article key={seat.session} className="rounded-2xl border border-stone-200 bg-white p-5">
          <h3 className="font-bold">{session.group} · Final seating plan</h3>
          <p className="mt-2 text-sm">{planDate(session.date)} · {session.shift === "Morning" ? "Morning" : "Afternoon"} · {session.time} IST</p>
          <p className="mt-2 text-lg font-bold">Room {seat.room}</p>
          <p className="mt-1">Row {seat.row}, Column {seat.column}</p>
          <p className="mt-3 text-xs text-stone-500">Position in the final room grid, counting from the top left and excluding blank spacer columns.</p>
        </article>
      );
    })}
  </section>
);
