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
import cs205bSeating from "../data/cs205b-seating.json";
import el106bRoster from "../data/el106b-roster.json";
import trackSeating from "../data/track-seating.json";
import cs336bRooms from "../data/cs336b-rooms.json";
import ai101bRooms from "../data/ai101b-rooms.json";
import cs302bSeating from "../data/cs302b-seating.json";
import it107bSeating from "../data/it107b-seating.json";
import { FinalAiResults } from "../components/FinalAiResults";
import { finalAiSessions, FinalAiSeat, getFinalAiSeats } from "../data/finalAiSeating";
import { planDate, roomwisePlans, searchSuppliedSeats, SuppliedSeat } from "../data/suppliedSeating";

interface BatchAllocation {
  section: string;
  group: number;
  room: string;
  batch: number;
}

interface Cs302bAllocation {
  shift: string;
  room: string;
  branch: string;
  section: string;
  page: number;
}

const cs302bByRegistration: Record<string, Cs302bAllocation> = cs302bSeating;

interface It107bAssignment {
  shift: string;
  room: string;
  page: number;
  source: string;
}

const it107bByRegistration: Record<string, It107bAssignment> = it107bSeating;

const cs205b: Record<string, BatchAllocation[]> = cs205bSeating;
const trackExams = {
  pps: { title: "Programming for Problem Solving (26IT101ESB)", date: "2026-11-18", evening: "2:00 PM – 4:00 PM" },
  ibm: { title: "IBM Track · Web Designing and Cloud Foundations", date: "2026-11-19", evening: "1:30 PM – 3:30 PM" },
};
type TrackSeat = { exam: string; shift: string; room: string };
const trackSeatsByUid: Record<string, TrackSeat[]> = trackSeating;
const el106bRosterByRegistration: Record<string, string> = el106bRoster;
const originalCs205bSession = "2026-11-23-morning-roomwise";
const batchTime = (batch: number) => batch === 1 ? "10:00 AM – 1:00 PM" : "1:30 PM – 4:30 PM";

export const StudentPortal: React.FC = () => {
  const [rollNumber, setRollNumber] = useState("");
  const [selectedDate, setSelectedDate] = useState<string>("");
  const [selectedShift, setSelectedShift] = useState<string>("");

  const [examinations, setExaminations] = useState<PublicExamination[]>([]);
  const [searching, setSearching] = useState<boolean>(false);

  const [searchResult, setSearchResult] = useState<StudentSearchResponse | null>(null);
  const [suppliedResult, setSuppliedResult] = useState<{ roll: string; seats: SuppliedSeat[] } | null>(null);
  const [batchResults, setBatchResults] = useState<BatchAllocation[]>([]);
  const [el106bBranch, setEl106bBranch] = useState<string | null>(null);
  const [trackResults, setTrackResults] = useState<TrackSeat[]>([]);
  const [cs336bRoom, setCs336bRoom] = useState<(typeof cs336bRooms)[number] | null>(null);
  const [ai101bMatches, setAi101bMatches] = useState<typeof ai101bRooms>([]);
  const [cs302bResult, setCs302bResult] = useState<Cs302bAllocation | null>(null);
  const [it107bResult, setIt107bResult] = useState<It107bAssignment | null>(null);
  const [finalAiResults, setFinalAiResults] = useState<FinalAiSeat[]>([]);
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

  const examDates = useMemo(() => Array.from(new Set([
    ...roomwisePlans.map(plan => plan.date),
    ...finalAiSessions.map(session => session.date),
    ...examinations.map(exam => exam.exam_date),
    "2026-11-18", "2026-11-19", "2026-11-20", "2026-11-23", "2026-11-25",
  ])).sort(), [examinations]);

  const handleSearch = async (event: React.FormEvent) => {
    event.preventDefault();
    const registration = rollNumber.trim().toUpperCase();
    setErrorMessage(null);
    setIsConnectionError(false);
    setFinalAiResults([]);
    setBatchResults([]);
    setEl106bBranch(null);
    setTrackResults([]);
    setCs336bRoom(null);
    setAi101bMatches([]);
    setCs302bResult(null);
    setIt107bResult(null);
    setSuppliedResult(null);
    setSearchResult(null);

    if (!registration) {
      setErrorMessage("Please enter your registration number or KIET UID to search.");
      return;
    }

    const matchesFilters = (date: string, shift: string) =>
      (!selectedDate || date === selectedDate) && (!selectedShift || shift === selectedShift);
    const finalAssignments = getFinalAiSeats(registration);
    const finalSeats = finalAssignments.filter(seat => {
      const session = finalAiSessions.find(item => item.id === seat.session)!;
      return matchesFilters(session.date, session.shift);
    });
    const batchAssignments = Object.prototype.hasOwnProperty.call(cs205b, registration) ? cs205b[registration] : [];
    const batches = batchAssignments.filter(seat => matchesFilters("2026-11-23", seat.batch === 1 ? "Morning" : "Evening"));
    const trackAssignments = Object.prototype.hasOwnProperty.call(trackSeatsByUid, registration) ? trackSeatsByUid[registration] : [];
    const tracks = trackAssignments.filter(seat => matchesFilters(seat.exam === "pps" ? trackExams.pps.date : trackExams.ibm.date, seat.shift));
    const cs302b = Object.prototype.hasOwnProperty.call(cs302bByRegistration, registration) ? cs302bByRegistration[registration] : undefined;
    const cs302bSeat = cs302b && matchesFilters("2026-11-25", cs302b.shift) ? cs302b : null;
    const it107b = Object.prototype.hasOwnProperty.call(it107bByRegistration, registration) ? it107bByRegistration[registration] : undefined;
    const it107bSeat = it107b && matchesFilters("2026-11-23", it107b.shift) ? it107b : null;
    const rosterBranch = Object.prototype.hasOwnProperty.call(el106bRosterByRegistration, registration) && matchesFilters("2026-11-20", "Morning")
      ? el106bRosterByRegistration[registration] : null;
    const namedAiRooms = ai101bRooms.filter(room => room.additional.includes(registration));
    const aiRooms = namedAiRooms.length ? namedAiRooms : ai101bRooms.filter(room =>
      /^\d{13}$/.test(registration) && registration >= room.start && registration <= room.end);
    const ai101bSeats = matchesFilters("2026-11-19", "Morning") ? aiRooms : [];
    const oopjSeat = /^\d{15}$/.test(registration) && matchesFilters("2026-11-19", "Morning")
      ? cs336bRooms.find(room => room.additional.includes(registration) || (registration >= room.start && registration <= room.end)) || null
      : null;

    const replacesFinalAi = (date: string, shift: string) => finalAssignments.some(seat => {
      const session = finalAiSessions.find(item => item.id === seat.session)!;
      return session.date === date && (date === "2026-11-23" || session.shift === shift);
    });

    setSearching(true);
    try {
      const supplied = await searchSuppliedSeats(registration, undefined, selectedShift || undefined, selectedDate || undefined);
      const seats = supplied.filter(seat =>
        !(!seat.plan.universityBatch && replacesFinalAi(seat.plan.date, seat.plan.shift)) &&
        !(batchAssignments.length && seat.plan.id === originalCs205bSession) &&
        !(cs302b && /^2026-11-25-(morning|evening)-roomwise$/.test(seat.plan.id)) &&
        !(it107b && /^2026-11-23-(morning|evening)-roomwise$/.test(seat.plan.id)) &&
        !(oopjSeat && seat.plan.id === "2026-11-19-morning-roomwise"));

      let publishedResult: StudentSearchResponse | null = null;
      let publishedUnavailable = false;
      if (examinations.some(exam => !selectedDate || exam.exam_date === selectedDate)) {
        try {
          const response = await apiClient.searchStudentSeating(registration, undefined, selectedShift || undefined);
          const allocations = response.allocations.filter(seat => !selectedDate || seat.exam_date === selectedDate);
          if (allocations.length) publishedResult = { ...response, allocations, total_allocations: allocations.length };
        } catch (error) {
          if (!(error instanceof ApiClientError && error.status === 404)) {
            publishedUnavailable = true;
            setErrorMessage("Additional published seating records could not be loaded. Please try again.");
          }
        }
      }

      setFinalAiResults(finalSeats);
      setBatchResults(batches);
      setTrackResults(tracks);
      setCs302bResult(cs302bSeat);
      setIt107bResult(it107bSeat);
      setEl106bBranch(rosterBranch);
      setAi101bMatches(ai101bSeats);
      setCs336bRoom(oopjSeat);
      setSearchResult(publishedResult);
      const hasResults = finalSeats.length || batches.length || tracks.length || cs302bSeat || it107bSeat || rosterBranch || ai101bSeats.length || oopjSeat || publishedResult;
      if (seats.length || (!hasResults && !publishedUnavailable)) setSuppliedResult({ roll: registration, seats });
    } catch {
      setErrorMessage("The seating plans could not be loaded. Please check your connection and try again.");
    } finally {
      setSearching(false);
    }
  };

  const combinedPdfUrl = searchResult
    ? apiClient.getSeatingSlipPdfUrl(
        searchResult.query_roll_number,
        searchResult.allocations.every(seat => seat.examination_id === searchResult.allocations[0]?.examination_id)
          ? searchResult.allocations[0]?.examination_id : undefined,
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
                    placeholder="Enter registration number, enrollment number, or KIET UID"
                    inputMode="text"
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
                  Exam Date (Optional)
                </label>
                <select
                  id="exam-filter"
                  value={selectedDate}
                  onChange={(e) => { setSelectedDate(e.target.value); setSelectedShift(""); }}
                  className="w-full px-3.5 py-3 rounded-xl border border-stone-200 bg-stone-50 text-stone-900 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-rose-500"
                >
                  <option value="">All exam dates</option>
                  {examDates.map(date => <option key={date} value={date}>{planDate(date)}</option>)}
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

        {finalAiResults.length > 0 && <FinalAiResults seats={finalAiResults} />}
        {it107bResult && (
          <section aria-live="polite" className="rounded-2xl border border-stone-200 bg-white p-5">
            <h2 className="text-xl font-bold">IT107B · Artificial Intelligence Essentials</h2>
            <p className="mt-2">23 November 2026 · {it107bResult.shift === "Morning" ? "Morning" : "Afternoon"} shift</p>
            <p className="mt-2 text-lg font-bold">Room {it107bResult.room}</p>
            <p className="mt-3 text-sm text-stone-600">The attendance sheet does not specify an exam time. Confirm the time with your exam coordinator.</p>
            <a
              href={`${import.meta.env.BASE_URL}${it107bResult.source}#page=${it107bResult.page}`}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-3 inline-block text-sm text-rose-700 underline"
            >View attendance sheet · page {it107bResult.page}</a>
          </section>
        )}
        {cs302bResult && (
          <section aria-live="polite" className="rounded-2xl border border-stone-200 bg-white p-5">
            <h2 className="text-xl font-bold">CS302B · Advanced Data Structure</h2>
            <p className="mt-2">25 November 2026 · {cs302bResult.shift} shift · {cs302bResult.shift === "Morning" ? "10:00 AM – 12:00 PM" : "2:00 PM – 4:00 PM"} IST</p>
            <p className="mt-1">{cs302bResult.branch} · Section {cs302bResult.section}</p>
            <p className="mt-2 text-lg font-bold">Room {cs302bResult.room}</p>
            <a
              href={`${import.meta.env.BASE_URL}seating-plans/cs302b-2026-11-25-${cs302bResult.shift.toLowerCase()}.pdf#page=${cs302bResult.page}`}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-3 inline-block text-sm text-rose-700 underline"
            >View seating plan · page {cs302bResult.page}</a>
          </section>
        )}
        {ai101bMatches.length > 0 && (
          <section aria-live="polite" className="rounded-2xl border border-stone-200 bg-white p-5">
            <h2 className="text-xl font-bold">AI101B · Introduction to AI</h2>
            <p className="mt-2">19 November 2026 · 10:00 AM – 12:00 PM IST</p>
            {ai101bMatches.map(({ room, section }) => (
              <p key={room} className="mt-2 font-bold">Room {room} · Section {section} · Side A</p>
            ))}
            <p className="mt-3 text-sm text-stone-600">{ai101bMatches.length > 1 ? "The published ranges overlap for this roll number. Confirm your room with the exam coordinator." : "Room based on the workbook’s roll-number ranges or individual entries."}</p>
          </section>
        )}
        {cs336bRoom && (
          <section aria-live="polite" className="rounded-2xl border border-stone-200 bg-white p-5">
            <h2 className="text-xl font-bold">CS336B · Object Oriented Programming with Java</h2>
            <p className="mt-2">19 November 2026 · 10:00 AM – 12:30 PM IST</p>
            <p className="mt-1">Batch {cs336bRoom.batch}</p>
            <p className="mt-2 text-lg font-bold">Room {cs336bRoom.room}</p>
            <p className="mt-3 text-sm text-stone-600">Matched against the published roll-number ranges and individual entries. Confirm your batch with the exam coordinator if needed.</p>
          </section>
        )}
        {trackResults.length > 0 && (
          <section aria-live="polite" className="space-y-3">
            <h2 className="text-xl font-bold">Your exam rooms</h2>
            {trackResults.map(seat => {
              const exam = seat.exam === "pps" ? trackExams.pps : trackExams.ibm;
              const time = seat.shift === "Morning" ? "10:00 AM – 12:00 PM" : exam.evening;
              return (
                <article key={seat.exam} className="rounded-2xl border border-stone-200 bg-white p-5">
                  <h3 className="font-bold">{exam.title}</h3>
                  <p className="mt-2 text-sm">{planDate(exam.date)} · {seat.shift} shift · {time} IST</p>
                  <p className="mt-2 text-lg font-bold">{seat.room}</p>
                </article>
              );
            })}
          </section>
        )}
        {el106bBranch && (
          <section aria-live="polite" className="rounded-2xl border border-stone-200 bg-white p-5">
            <h2 className="text-xl font-bold">EL106B · Introduction to AI &amp; ML</h2>
            <p className="mt-2">20 November 2026 · 10:00 AM – 12:00 PM IST</p>
            <p className="mt-1">{el106bBranch} · Section A · Year II</p>
            <p className="mt-3 text-sm text-stone-600">Your registration number is on the exam roster. Your room and seat assignment are unavailable.</p>
          </section>
        )}
        {batchResults.length > 0 && (
          <section aria-live="polite" className="space-y-3">
            <h2 className="text-xl font-bold">CS205B seating · 23 November 2026</h2>
            {batchResults.length > 1 && <p className="text-sm text-amber-800">This registration number has multiple entries. Confirm your section and batch with your exam coordinator.</p>}
            {batchResults.map(({ section, group, room, batch }, index) => (
              <article key={index} className="rounded-2xl border border-stone-200 bg-white p-5">
                <h3 className="text-lg font-bold">{room}</h3>
                <p>{section} · Group {group} · Batch {batch}</p>
                <p className="text-sm text-stone-600">{batchTime(batch)} IST</p>
              </article>
            ))}
          </section>
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
