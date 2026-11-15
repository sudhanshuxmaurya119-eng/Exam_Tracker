import React, { useEffect, useMemo, useState } from "react";
import {
  FileDown,
  Loader2,
  Search,
  UserCheck,
} from "lucide-react";
import { apiClient, ApiClientError } from "../api/client";
import { PublicExamination, StudentSearchResponse } from "../types";
import { SeatingCard } from "../components/SeatingCard";
import { StatusBanner } from "../components/StatusBanner";
import { SuppliedSeatResults } from "../components/SuppliedSeatResults";
import { planDate, planTime, roomwisePlans, searchSuppliedSeats, SuppliedSeat } from "../data/suppliedSeating";

export const StudentPortal: React.FC = () => {
  const [rollNumber, setRollNumber] = useState("");
  const [selectedExamId, setSelectedExamId] = useState<string>("");
  const [selectedShift, setSelectedShift] = useState<string>("");

  const [examinations, setExaminations] = useState<PublicExamination[]>([]);
  const [searching, setSearching] = useState<boolean>(false);

  const [searchResult, setSearchResult] = useState<StudentSearchResponse | null>(null);
  const [suppliedResult, setSuppliedResult] = useState<{ roll: string; seats: SuppliedSeat[] } | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isConnectionError, setIsConnectionError] = useState<boolean>(false);

  useEffect(() => {
    let active = true;
    apiClient
      .getPublicExaminations()
      .then((data) => {
        if (active) {
          setExaminations(data);
          setIsConnectionError(false);
        }
      })
      .catch((err: unknown) => {
        if (!active) return;
        if (err instanceof ApiClientError && err.isConnectionError) {
          setIsConnectionError(true);
        }
      });
    return () => {
      active = false;
    };
  }, []);

  const availableShifts = useMemo(() => {
    const set = new Set<string>(["Morning", "Evening"]);
    examinations.forEach((e) => {
      if (e.shift) set.add(e.shift);
    });
    return Array.from(set);
  }, [examinations]);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = rollNumber.trim().toUpperCase();
    if (!trimmed) {
      setErrorMessage("Please enter your University Registration Number to search.");
      return;
    }
    if ((!selectedExamId || selectedExamId.startsWith("plan:")) && !/^\d{15}$/.test(trimmed)) {
      setErrorMessage("Please enter your complete 15-digit registration number from the supplied seating plans.");
      setSuppliedResult(null);
      return;
    }

    setSearching(true);
    setErrorMessage(null);
    setIsConnectionError(false);
    setSuppliedResult(null);
    setSearchResult(null);

    try {
      if (!selectedExamId || selectedExamId.startsWith("plan:")) {
        const seats = await searchSuppliedSeats(trimmed, selectedExamId.replace(/^plan:/, "") || undefined, selectedShift || undefined);
        setSuppliedResult({ roll: trimmed, seats });
        return;
      }
      const examIdNum = selectedExamId ? Number(selectedExamId) : undefined;
      const shiftVal = selectedShift || undefined;
      const result = await apiClient.searchStudentSeating(trimmed, examIdNum, shiftVal);
      setSearchResult(result);
    } catch (err: unknown) {
      setSearchResult(null);
      if (err instanceof ApiClientError) {
        setIsConnectionError(err.isConnectionError);
        setErrorMessage(err.message);
      } else {
        setErrorMessage("The seating plans could not be loaded. Please check your connection and try again.");
      }
    } finally {
      setSearching(false);
    }
  };

  const combinedPdfUrl = searchResult
    ? apiClient.getSeatingSlipPdfUrl(
        searchResult.query_roll_number,
        selectedExamId ? Number(selectedExamId) : undefined,
        selectedShift || undefined
      )
    : "";

  return (
    <div className="baymax-portal flex flex-col">
      <section className="baymax-hero px-4 sm:px-6 lg:px-8">
        <div className="relative mx-auto max-w-6xl py-10 sm:py-16 lg:py-20">
          <div className="relative z-10 max-w-xl">
            <p className="mb-5 inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.16em] text-stone-200 sm:text-xs"><span className="h-1.5 w-1.5 rounded-full bg-rose-400" /> November 2026 · MSE / MSE-2</p>
            <h1 className="text-4xl font-extrabold leading-[1.08] tracking-tight text-white sm:text-6xl">Hello there.<br />Let's find your seat<span className="text-rose-400">.</span></h1>
            <p className="mt-5 max-w-md text-sm leading-relaxed text-stone-300 sm:text-base">A little help before your big day. Enter your registration number, and leave the room-finding to us.</p>
          </div>
          <p className="baymax-hello" aria-hidden="true">Your personal exam companion.</p>
        </div>
      </section>
      <div className="relative z-10 mx-auto -mt-5 w-full max-w-6xl px-4 sm:-mt-8 sm:px-6 lg:px-8">
        <div className="max-w-2xl">
          <div className="mb-4 flex items-center gap-2 px-1 pt-10"><Search className="h-4 w-4 text-rose-600" /><h2 className="text-lg font-bold text-stone-950">Find My Seat</h2></div>
          <form
            onSubmit={handleSearch}
            className="seat-search-card rounded-3xl border border-stone-200 bg-white p-5 text-left shadow-xl shadow-black/5 sm:p-7"
          >
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {/* Roll Number Input */}
              <div className="sm:col-span-2 min-w-0">
                <label
                  htmlFor="roll-number-input"
                  className="block text-xs font-semibold uppercase tracking-wider text-stone-600 mb-1.5"
                >
                  Student Registration Number *
                </label>
                <div className="relative">
                  <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                  <input
                    id="roll-number-input"
                    type="text"
                    value={rollNumber}
                    onChange={(e) => setRollNumber(e.target.value.toUpperCase())}
                    placeholder="Enter your full registration number"
                    inputMode={!selectedExamId || selectedExamId.startsWith("plan:") ? "numeric" : "text"}
                    className="w-full pl-10 pr-4 py-3 rounded-xl border border-stone-200 bg-stone-50 text-stone-900 placeholder-slate-400 font-semibold text-sm focus:outline-none focus:ring-2 focus:ring-rose-500"
                    required
                  />
                </div>
              </div>

              {/* Optional Examination Filter */}
              <div className="min-w-0">
                <label
                  htmlFor="exam-filter"
                  className="block text-xs font-semibold uppercase tracking-wider text-stone-600 mb-1.5"
                >
                  Select Examination (Optional)
                </label>
                <select
                  id="exam-filter"
                  value={selectedExamId}
                  onChange={(e) => { setSelectedExamId(e.target.value); setSelectedShift(""); }}
                  className="w-full px-3.5 py-3 rounded-xl border border-stone-200 bg-stone-50 text-stone-900 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-rose-500"
                >
                  <option value="">All supplied roomwise plans (18–27 Nov)</option>
                  <optgroup label="MSE / MSE-2 · November 2026">
                    {roomwisePlans.map(plan => <option key={plan.id} value={`plan:${plan.id}`}>
                      {planDate(plan.date)} · {plan.shift} · {planTime(plan.shift)}
                    </option>)}
                  </optgroup>
                  {examinations.length > 0 && <optgroup label="Other published examinations">
                  {examinations.map((exam) => (
                    <option key={exam.id} value={exam.id}>
                      {exam.exam_code} — {exam.title} ({exam.shift})
                    </option>
                  ))}
                  </optgroup>}
                </select>
              </div>

              {/* Optional Shift Filter */}
              <div className="min-w-0">
                <label
                  htmlFor="shift-filter"
                  className="block text-xs font-semibold uppercase tracking-wider text-stone-600 mb-1.5"
                >
                  Shift (Optional)
                </label>
                <select
                  id="shift-filter"
                  value={selectedShift}
                  onChange={(e) => setSelectedShift(e.target.value)}
                  className="w-full px-3.5 py-3 rounded-xl border border-stone-200 bg-stone-50 text-stone-900 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-rose-500"
                >
                  <option value="">All Shifts</option>
                  {availableShifts.map((shift) => (
                    <option key={shift} value={shift}>
                      {shift}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="mt-4 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
              <span className="text-xs text-stone-500">
                Your room and seat, one simple search away.
              </span>
              <button
                type="submit"
                disabled={searching}
                className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-rose-600 hover:bg-rose-700 disabled:opacity-60 text-white font-semibold text-sm shadow-lg shadow-rose-600/15 transition"
              >
                {searching ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Searching Seating Plan...
                  </>
                ) : (
                  <>
                    <Search className="w-4 h-4" />
                    Find My Seat
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>

      {/* Results & Published Schedule Section */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {errorMessage && (
          <StatusBanner
            type={isConnectionError ? "connection-error" : "error"}
            title={
              isConnectionError ? "Backend Connection Error" : "Unable to Search Seating Plans"
            }
            message={errorMessage}
            onDismiss={() => setErrorMessage(null)}
          />
        )}

        {suppliedResult && <SuppliedSeatResults roll={suppliedResult.roll} seats={suppliedResult.seats} />}

        {/* Student Search Results */}
        {searchResult && (
          <div className="space-y-6">
            <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div className="flex items-start gap-3.5">
                <div className="w-12 h-12 rounded-2xl bg-indigo-100 text-indigo-700 flex items-center justify-center shrink-0">
                  <UserCheck className="w-6 h-6" />
                </div>
                <div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <h2 className="text-xl font-bold text-slate-900">
                      {searchResult.student_name}
                    </h2>
                    <span className="px-2.5 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200 text-xs font-bold">
                      {searchResult.query_roll_number}
                    </span>
                  </div>
                  <p className="text-sm text-slate-600 mt-0.5">
                    {searchResult.department || "University Candidate"} • Found{" "}
                    <strong className="text-slate-900">
                      {searchResult.total_allocations}
                    </strong>{" "}
                    seating allocation(s)
                  </p>
                </div>
              </div>

              <a
                href={combinedPdfUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-sm font-semibold shadow-sm transition"
              >
                <FileDown className="w-4 h-4" />
                Download Complete Seating Slip (PDF)
              </a>
            </div>

            <div className="space-y-5">
              {searchResult.allocations.map((alloc) => (
                <SeatingCard key={alloc.seating_id} allocation={alloc} />
              ))}
            </div>
          </div>
        )}

      </main>
    </div>
  );
};
