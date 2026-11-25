import React from "react";
import { finalAiSessions, FinalAiSeat } from "../data/finalAiSeating";
import { planDate } from "../data/suppliedSeating";

export const FinalAiResults: React.FC<{ seats: FinalAiSeat[] }> = ({ seats }) => {
  const assignments = seats.map(seat => ({
    ...seat,
    details: finalAiSessions.find(session => session.id === seat.session)!,
  }));
  const subjects = Array.from(new Set(assignments.map(seat => seat.details.subject)));

  return (
    <div className="space-y-6">
      {subjects.map(subject => (
        <section key={subject} aria-live="polite" className="space-y-3">
          <h2 className="text-xl font-bold">{subject}</h2>
          {assignments.filter(seat => seat.details.subject === subject).map(seat => (
            <article key={seat.session} className="rounded-2xl border border-stone-200 bg-white p-5">
              <h3 className="font-bold">{seat.details.group} · {seat.details.subject.startsWith("AI201B ") ? "Final seating plan" : "Seating plan"}</h3>
              <p className="mt-2 text-sm">{planDate(seat.details.date)} · {seat.details.shift === "Morning" ? "Morning" : "Afternoon"} · {seat.details.time} IST</p>
              <p className="mt-2 text-lg font-bold">Room {seat.room}</p>
              {seat.row !== undefined && seat.column !== undefined ? (
                <>
                  <p className="mt-1">Row {seat.row}, Column {seat.column}</p>
                  <p className="mt-3 text-xs text-stone-500">Position in the final room grid, counting from the top left and excluding blank spacer columns.</p>
                </>
              ) : (
                <p className="mt-3 text-xs text-stone-500">Room allocation from the supplied registration-number ranges and individual entries.</p>
              )}
            </article>
          ))}
        </section>
      ))}
    </div>
  );
};
