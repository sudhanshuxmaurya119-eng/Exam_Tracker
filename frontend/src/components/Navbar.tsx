import React from "react";
import { NavLink } from "react-router-dom";
import { CalendarDays, Search } from "lucide-react";

export const Navbar: React.FC = () => (
  <header className="sticky top-0 z-40 border-b border-stone-200 bg-white/95 backdrop-blur-xl">
    <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-3 px-4 py-3 min-[480px]:flex-row sm:px-6 lg:px-8">
      <div className="flex items-center gap-3">
        <span className="baymax-face" aria-hidden="true"><i /><i /></span>
        <div><p className="text-sm font-extrabold tracking-tight text-stone-950 sm:text-base">Exam Companion<span className="text-rose-600">.</span></p><p className="text-[10px] uppercase tracking-[0.18em] text-stone-500">A little less exam stress</p></div>
      </div>
      <nav aria-label="Main navigation" className="flex w-full gap-1 rounded-full bg-stone-100 p-1 min-[480px]:w-auto">
        {[{ to: "/", label: "Find My Seat", icon: Search }, { to: "/timetable", label: "Timetable", icon: CalendarDays }].map(({ to, label, icon: Icon }) => (
          <NavLink key={to} to={to} end className={({ isActive }) => `flex flex-1 items-center justify-center gap-2 whitespace-nowrap rounded-full px-4 py-2.5 text-xs font-semibold transition sm:text-sm ${isActive ? "bg-stone-950 text-white shadow-sm" : "text-stone-600 hover:bg-white hover:text-stone-950"}`}><Icon className="h-4 w-4" />{label}</NavLink>
        ))}
      </nav>
    </div>
  </header>
);
