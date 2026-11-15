import React from "react";
import { Building2, DoorOpen, FileDown, Layers, Search } from "lucide-react";
import { assetUrl, planDate, planTime, SuppliedSeat } from "../data/suppliedSeating";

export const SuppliedSeatResults: React.FC<{ roll: string; seats: SuppliedSeat[] }> = ({ roll, seats }) => (
  <section aria-labelledby="supplied-results-heading" aria-live="polite" className="space-y-4">
    <div>
      <h2 id="supplied-results-heading" className="break-words text-xl font-bold text-slate-900">{seats.length ? "Your examination seats" : "No matching seat found"}</h2>
      <p className="mt-1 break-words text-sm text-slate-600">Roll number: <strong className="break-all">{roll}</strong> · {seats.length} allocation{seats.length !== 1 ? "s" : ""} in the supplied roomwise plans</p>
    </div>
    {!seats.length && <div className="rounded-2xl border border-amber-200 bg-amber-50 p-5 text-sm leading-relaxed text-amber-900"><Search className="mb-2 h-5 w-5" />Check your full roll number, examination and shift. Only seats explicitly listed in the supplied PDFs are searchable. Try another examination or shift, and check that your roll number is complete.</div>}
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">{seats.map((seat, i) => <article key={`${seat.plan.id}-${i}`} className="min-w-0 rounded-2xl bg-stone-950 p-5 text-white shadow-lg sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-2"><h3 className="font-bold">{planDate(seat.plan.date)}</h3><span className="rounded-full bg-rose-500/20 px-3 py-1 text-xs font-semibold text-rose-200">{seat.plan.shift} shift</span></div>
      <p className="mt-2 text-sm text-slate-300">{planTime(seat.plan.shift)} IST · MSE / MSE-2</p>
      <dl className="mt-5 space-y-4">
        <div className="flex items-center gap-3"><Building2 className="h-5 w-5 shrink-0 text-rose-300" /><div><dt className="text-xs text-slate-400">Building</dt><dd className="text-lg font-bold">Block {seat.building}</dd></div></div>
        <div className="flex items-center gap-3"><Layers className="h-5 w-5 shrink-0 text-rose-300" /><div><dt className="text-xs text-slate-400">Floor</dt><dd className="text-lg font-bold">{seat.floor || "Not stated in this plan"}</dd></div></div>
        <div className="flex items-center gap-3"><DoorOpen className="h-5 w-5 shrink-0 text-rose-300" /><div><dt className="text-xs text-slate-400">Room</dt><dd className="text-2xl font-bold">{seat.room}</dd></div></div>
        <div className="rounded-xl bg-white p-4 text-stone-950"><dt className="text-xs font-semibold uppercase tracking-wide">Seat position</dt><dd className="mt-1 text-2xl font-extrabold sm:text-3xl">Row {seat.row}, Column {seat.column}</dd></div>
      </dl>
      <p className="mt-3 text-xs leading-relaxed text-slate-400">Rows count from the top of the PDF grid; columns count from left to right, excluding aisle gaps. Confirm your position in the original plan.</p>
      <a href={`${assetUrl(seat.plan.url)}#page=${seat.page}`} target="_blank" rel="noopener noreferrer" className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-xl border border-slate-600 px-4 py-3 text-sm font-semibold hover:bg-slate-800"><FileDown className="h-4 w-4" /> View room plan · page {seat.page}</a>
    </article>)}</div>
  </section>
);
