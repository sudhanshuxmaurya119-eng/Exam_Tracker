import React, { useMemo, useState } from "react";
import { CalendarDays, FileDown, Search, X } from "lucide-react";
import timetable from "../data/timetable.json";

const normalize = (value: string) => value.toLowerCase().replace(/[^a-z0-9]/g, "");
const dateLabel = (value: string) => new Date(`${value}T00:00:00`).toLocaleDateString("en-IN", {
  weekday: "short", day: "numeric", month: "short", year: "numeric",
});
const examTime = (entry: (typeof timetable)[number]) => entry.subject.startsWith("CS205B ")
  ? "10:00 AM – 1:00 PM or 1:30 PM – 4:30 PM (check your assigned batch in Find My Seat)"
  : `${entry.start} – ${entry.end}`;

const options = (values: string[]) => Array.from(new Set(values)).sort();
const inputClass = "w-full min-w-0 rounded-xl border border-slate-300 bg-white px-3 py-3 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-rose-500";

export const ExamTimetable: React.FC = () => {
  const [query, setQuery] = useState("");
  const [program, setProgram] = useState("");
  const [semester, setSemester] = useState("");
  const [branch, setBranch] = useState("");
  const [date, setDate] = useState("");
  const branches = options(timetable.filter(e => (!program || e.program === program) && (!semester || e.semester === semester)).map(e => e.branch));
  const semesters = ["I", "III", "V", "VII"].filter(s => timetable.some(e => e.semester === s && (!program || e.program === program)));
  const filtered = useMemo(() => {
    const words = query.trim().split(/\s+/).map(normalize).filter(Boolean);
    return timetable.filter(e => (!program || e.program === program) && (!semester || e.semester === semester)
      && (!branch || e.branch === branch) && (!date || e.date === date)
      && words.every(word => normalize(`${e.subject} ${e.program} ${e.branch} ${e.exam} ${e.mode} ${e.date} ${dateLabel(e.date)}`).includes(word)));
  }, [query, program, semester, branch, date]);
  const active = query || program || semester || branch || date;

  return (
    <section id="exam-timetable" aria-labelledby="timetable-heading" className="scroll-mt-20 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="p-4 sm:p-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <p className="text-xs font-bold uppercase tracking-wider text-rose-600">November 2026 · Session 2026–27</p>
            <h2 id="timetable-heading" className="mt-2 flex items-center gap-2 text-xl font-bold text-slate-900"><CalendarDays className="h-5 w-5 shrink-0 text-rose-600" /> Exam timetable</h2>
            <p className="mt-2 text-sm text-slate-600">MSE 2 & PUE · 18–28 November. Find your paper without a roll number.</p>
          </div>
          <a href={`${import.meta.env.BASE_URL}exam-datesheet-november-2026.pdf`} target="_blank" rel="noopener noreferrer" className="inline-flex shrink-0 items-center justify-center gap-2 rounded-xl border border-rose-200 px-4 py-3 text-sm font-semibold text-rose-700 hover:bg-rose-50">
            <FileDown className="h-4 w-4" /> Official datesheet (PDF)
          </a>
        </div>
        <div role="search" aria-label="Search exam timetable" className="mt-5 space-y-4">
          <div>
            <label htmlFor="timetable-search" className="mb-1.5 block text-sm font-semibold text-slate-700">Search timetable</label>
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-3.5 h-4 w-4 text-slate-400" />
              <input id="timetable-search" type="search" value={query} onChange={e => setQuery(e.target.value)} placeholder="Search subject, course code or branch…" className={`${inputClass} pl-10`} />
            </div>
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <label className="min-w-0 text-xs font-semibold text-slate-600">Programme
              <select aria-label="Programme" value={program} onChange={e => { setProgram(e.target.value); setSemester(""); setBranch(""); }} className={`${inputClass} mt-1.5`}>
                <option value="">All programmes</option>{options(timetable.map(e => e.program)).map(p => <option key={p}>{p}</option>)}
              </select>
            </label>
            <label className="min-w-0 text-xs font-semibold text-slate-600">Semester
              <select aria-label="Semester" value={semester} onChange={e => { setSemester(e.target.value); setBranch(""); }} className={`${inputClass} mt-1.5`}>
                <option value="">All semesters</option>{semesters.map(s => <option key={s} value={s}>Semester {s}</option>)}
              </select>
            </label>
            <label className="min-w-0 text-xs font-semibold text-slate-600">Branch / Specialisation
              <select aria-label="Branch / Specialisation" value={branch} onChange={e => setBranch(e.target.value)} className={`${inputClass} mt-1.5`}>
                <option value="">All branches</option>{branches.map(b => <option key={b}>{b}</option>)}
              </select>
            </label>
            <label className="min-w-0 text-xs font-semibold text-slate-600">Exam date
              <select aria-label="Exam date" value={date} onChange={e => setDate(e.target.value)} className={`${inputClass} mt-1.5`}>
                <option value="">All dates</option>{options(timetable.map(e => e.date)).map(d => <option key={d} value={d}>{dateLabel(d)}</option>)}
              </select>
            </label>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
          <p aria-live="polite" role="status" className="text-sm text-slate-600">{filtered.length} {filtered.length === 1 ? "exam entry" : "exam entries"}{program && ` · ${program}`}{semester && ` · Semester ${semester}`}{branch && ` · ${branch}`}</p>
          {active && <button type="button" onClick={() => { setQuery(""); setProgram(""); setSemester(""); setBranch(""); setDate(""); }} className="inline-flex items-center gap-1 rounded-lg px-3 py-2 text-sm font-semibold text-rose-700 hover:bg-rose-50"><X className="h-4 w-4" /> Clear filters</button>}
        </div>
        <p className="mt-3 text-xs leading-relaxed text-slate-500">All times are IST. Electives separated by “/” are alternatives; attend your enrolled course. SAP restrictions are shown with the paper. Check the linked PDF for official details and exam mode colour coding.</p>
      </div>
      {filtered.length === 0 ? <div className="border-t border-slate-200 bg-slate-50 px-5 py-12 text-center"><h3 className="font-semibold text-slate-800">No exams match your filters</h3><p className="mt-2 text-sm text-slate-500">Try a different subject or clear the filters to see the full timetable.</p></div> : (
        <>
          <div className="hidden md:block">
            <table className="w-full table-fixed text-left text-sm">
              <caption className="sr-only">November 2026 MSE 2 and PUE exam timetable. All times in IST.</caption>
              <thead className="border-y border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500"><tr><th scope="col" className="w-[18%] p-4">Date</th><th scope="col" className="w-[19%] p-4">Time (IST)</th><th scope="col" className="w-[24%] p-4">Programme / Branch</th><th scope="col" className="p-4">Paper / Course</th></tr></thead>
              <tbody className="divide-y divide-slate-100">{filtered.map(e => <tr key={e.id} className="align-top hover:bg-rose-50/30"><td className="p-4 font-semibold text-slate-800"><time dateTime={e.date}>{dateLabel(e.date)}</time><span className="mt-1 block text-xs font-normal text-rose-600">{e.exam}</span></td><td className="p-4 text-slate-600">{examTime(e)}</td><td className="break-words p-4 text-slate-700"><span className="font-semibold">{e.program} · {e.branch === e.program ? `Sem ${e.semester}` : e.branch}</span><span className="mt-1 block text-xs text-slate-500">Semester {e.semester}</span></td><td className="break-words p-4 font-medium leading-relaxed text-slate-900">{e.subject}{e.mode && <span className="mt-1 block text-xs font-normal text-slate-500">{e.mode}</span>}<a href={`${import.meta.env.BASE_URL}exam-datesheet-november-2026.pdf#page=${e.page}`} target="_blank" rel="noopener noreferrer" className="mt-2 block text-xs font-normal text-rose-600 underline">Source · page {e.page}</a></td></tr>)}</tbody>
            </table>
          </div>
          <div className="space-y-3 border-t border-slate-200 bg-slate-50 p-4 md:hidden">{filtered.map(e => <article key={e.id} className="min-w-0 rounded-xl border border-slate-200 bg-white p-4">
            <div className="flex flex-wrap items-center justify-between gap-2"><time dateTime={e.date} className="text-sm font-bold text-rose-700">{dateLabel(e.date)}</time><span className="rounded bg-rose-50 px-2 py-1 text-xs font-semibold text-rose-700">{e.exam}</span></div>
            <p className="mt-2 text-sm font-semibold text-slate-600">{examTime(e)} IST</p>
            <h3 className="mt-3 break-words text-sm font-bold leading-relaxed text-slate-900">{e.subject}</h3>
            <p className="mt-3 break-words text-xs text-slate-500">{e.program}{e.branch !== e.program && ` · ${e.branch}`} · Semester {e.semester}{e.mode && ` · ${e.mode}`}</p>
            <a href={`${import.meta.env.BASE_URL}exam-datesheet-november-2026.pdf#page=${e.page}`} target="_blank" rel="noopener noreferrer" className="mt-3 inline-block text-xs text-rose-700 underline">View official datesheet · page {e.page}</a>
          </article>)}</div>
        </>
      )}
    </section>
  );
};
