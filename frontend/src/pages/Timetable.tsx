import React from "react";
import { ExamTimetable } from "../components/ExamTimetable";

export const Timetable: React.FC = () => (
  <main className="baymax-portal mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 sm:py-12 lg:px-8">
    <div className="mb-7"><p className="mb-3 text-xs font-bold uppercase tracking-[0.2em] text-rose-600">Your exam companion</p><h1 className="text-3xl font-extrabold tracking-tight text-stone-950 sm:text-4xl">A clear plan. A calmer you.</h1><p className="mt-3 text-sm text-stone-600">Find your papers, dates, and times in one place.</p></div>
    <ExamTimetable />
  </main>
);
