import React, { useState } from "react";
import { CalendarDays, Download, FileText } from "lucide-react";
import { assetUrl, planDate, planTime, roomwisePlans, suppliedPlans } from "../data/suppliedSeating";

export const SuppliedSeatingPlans: React.FC = () => {
  const [date, setDate] = useState("");
  const [shift, setShift] = useState("");
  const sessions = roomwisePlans.filter(p => (!date || p.date === date) && (!shift || p.shift === shift));
  return <section id="seating-plans" aria-labelledby="seating-plans-heading" className="scroll-mt-20 rounded-2xl border border-indigo-200 bg-white p-4 shadow-sm sm:p-6">
    <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
      <div className="min-w-0"><p className="text-xs font-bold uppercase tracking-wider text-indigo-600">Examination notice · Odd semester 2026–27</p><h2 id="seating-plans-heading" className="mt-2 text-xl font-bold leading-snug text-slate-900">Consolidated & Roomwise Seating Plan for MSE/MSE-2</h2><p className="mt-3 text-sm leading-relaxed text-slate-600">For <strong>2nd and 3rd Year B.Tech./B.Pharm.</strong> and <strong>2nd Year MBA/MCA/M.Pharm./M.Tech.</strong> students for examinations scheduled from <strong>18 to 27 November 2026.</strong></p></div>
      <a href={assetUrl("seating-plans/all-seating-plans-november-2026.zip")} download className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white hover:bg-indigo-500"><Download className="h-4 w-4" /> Download all plans (ZIP)</a>
    </div>
    <p className="mt-4 text-sm text-slate-600">Use the roll-number search above to find your seat, or open a plan below. Consolidated plans show room allocations; roomwise plans show the seating grid.</p>
    <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2">
      <div><label htmlFor="plan-date" className="mb-1.5 block text-xs font-semibold text-slate-600">Plan date</label><select id="plan-date" value={date} onChange={e => setDate(e.target.value)} className="w-full rounded-xl border border-slate-300 bg-white p-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"><option value="">All dates</option>{Array.from(new Set(roomwisePlans.map(p => p.date))).map(d => <option key={d} value={d}>{planDate(d)}</option>)}</select></div>
      <div><label htmlFor="plan-shift" className="mb-1.5 block text-xs font-semibold text-slate-600">Plan shift</label><select id="plan-shift" value={shift} onChange={e => setShift(e.target.value)} className="w-full rounded-xl border border-slate-300 bg-white p-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"><option value="">All shifts</option><option>Morning</option><option>Evening</option></select></div>
    </div>
    <p className="mt-4 text-xs text-slate-500" role="status">{sessions.length} examination sessions · All times IST</p>
    <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">{sessions.map(plan => {
      const consolidated = suppliedPlans.find(p => p.date === plan.date && p.shift === plan.shift && p.kind === "consolidated");
      return <article key={plan.id} className="min-w-0 rounded-xl border border-slate-200 bg-slate-50 p-4"><h3 className="flex flex-wrap items-center gap-2 font-bold text-slate-800"><CalendarDays className="h-4 w-4 text-indigo-600" />{planDate(plan.date)}<span className="text-xs font-medium text-indigo-700">{plan.shift}</span></h3><p className="mt-2 text-xs text-slate-500">{planTime(plan.shift)} · {plan.pages} roomwise pages</p><div className="mt-3 flex flex-wrap gap-2"><a href={assetUrl(plan.url)} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5 rounded-lg border border-indigo-200 bg-white px-3 py-2.5 text-xs font-semibold text-indigo-700 hover:bg-indigo-50"><FileText className="h-4 w-4" /> Roomwise PDF</a>{consolidated ? <a href={assetUrl(consolidated.url)} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-xs font-semibold text-slate-700 hover:bg-slate-100"><FileText className="h-4 w-4" /> Consolidated PDF</a> : <p className="self-center text-xs text-slate-500">Consolidated plan not supplied</p>}</div></article>;
    })}</div>
    {!sessions.length && <p className="mt-4 rounded-xl bg-slate-50 p-5 text-center text-sm text-slate-600">No plans were supplied for this date and shift.</p>}
  </section>;
};
