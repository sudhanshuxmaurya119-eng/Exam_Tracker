import React from "react";
import {
  BookOpen,
  Building,
  Calendar,
  Clock,
  FileDown,
  Info,
  Layers,
  MapPin,
} from "lucide-react";
import { StudentSeatingAllocation } from "../types";
import { apiClient } from "../api/client";

interface SeatingCardProps {
  allocation: StudentSeatingAllocation;
}

export const SeatingCard: React.FC<SeatingCardProps> = ({ allocation }) => {
  const pdfUrl = apiClient.getSeatingSlipPdfUrl(
    allocation.roll_number,
    allocation.examination_id
  );

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm hover:shadow-md transition overflow-hidden">
      {/* Card Top Banner */}
      <div className="bg-gradient-to-r from-indigo-900 via-indigo-800 to-slate-900 px-5 py-4 text-white flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="px-2.5 py-0.5 rounded-md bg-indigo-500/30 border border-indigo-400/40 text-xs font-semibold tracking-wider uppercase">
              {allocation.exam_code}
            </span>
            <span className="px-2.5 py-0.5 rounded-md bg-amber-500/20 border border-amber-400/40 text-amber-200 text-xs font-medium">
              {allocation.shift}
            </span>
          </div>
          <h3 className="text-lg font-bold mt-1.5">{allocation.examination_title}</h3>
        </div>

        <a
          href={pdfUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center justify-center gap-2 px-3.5 py-2 rounded-xl bg-white/15 hover:bg-white/25 text-white text-xs sm:text-sm font-medium border border-white/20 transition self-start sm:self-auto"
        >
          <FileDown className="w-4 h-4" />
          Download Seating Slip PDF
        </a>
      </div>

      {/* Prominent Hall / Room & Seat Highlight */}
      <div className="p-5">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
          <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-3.5 text-center">
            <span className="text-xs font-semibold uppercase tracking-wider text-indigo-600 block">
              Room / Hall No.
            </span>
            <span className="text-2xl font-extrabold text-indigo-950 mt-1 block">
              {allocation.room_number}
            </span>
          </div>

          <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3.5 text-center">
            <span className="text-xs font-semibold uppercase tracking-wider text-emerald-700 block">
              Allocated Seat No.
            </span>
            <span className="text-2xl font-extrabold text-emerald-950 mt-1 block">
              {allocation.seat_number}
            </span>
          </div>

          <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 text-center">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 block">
              Bench / Desk
            </span>
            <span className="text-lg font-bold text-slate-800 mt-1.5 block">
              {allocation.bench_number || "Standard"}
            </span>
          </div>

          <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 text-center">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 block">
              Row / Column
            </span>
            <span className="text-lg font-bold text-slate-800 mt-1.5 block">
              {allocation.row_number || "-"} / {allocation.column_number || "-"}
            </span>
          </div>
        </div>

        {/* Detailed Metadata Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 text-sm border-t border-slate-100 pt-4">
          <div className="flex items-start gap-2.5">
            <Calendar className="w-4 h-4 text-indigo-600 mt-0.5 shrink-0" />
            <div>
              <span className="text-xs text-slate-500 block">Examination Date</span>
              <span className="font-semibold text-slate-800">{allocation.exam_date}</span>
            </div>
          </div>

          <div className="flex items-start gap-2.5">
            <Clock className="w-4 h-4 text-indigo-600 mt-0.5 shrink-0" />
            <div>
              <span className="text-xs text-slate-500 block">Shift & Timing</span>
              <span className="font-semibold text-slate-800">
                {allocation.shift}
                {allocation.start_time && allocation.end_time
                  ? ` (${allocation.start_time} - ${allocation.end_time})`
                  : ""}
              </span>
            </div>
          </div>

          <div className="flex items-start gap-2.5">
            <BookOpen className="w-4 h-4 text-indigo-600 mt-0.5 shrink-0" />
            <div>
              <span className="text-xs text-slate-500 block">Subject / Course</span>
              <span className="font-semibold text-slate-800">
                {allocation.subject_name || "Scheduled Paper"}
                {allocation.subject_code ? ` (${allocation.subject_code})` : ""}
              </span>
            </div>
          </div>

          <div className="flex items-start gap-2.5">
            <Building className="w-4 h-4 text-indigo-600 mt-0.5 shrink-0" />
            <div>
              <span className="text-xs text-slate-500 block">Academic Building</span>
              <span className="font-semibold text-slate-800">
                {allocation.building_name || "Main Examination Block"}
              </span>
            </div>
          </div>

          <div className="flex items-start gap-2.5">
            <Layers className="w-4 h-4 text-indigo-600 mt-0.5 shrink-0" />
            <div>
              <span className="text-xs text-slate-500 block">Floor Level</span>
              <span className="font-semibold text-slate-800">
                {allocation.floor_number || "Ground Floor"}
              </span>
            </div>
          </div>

          <div className="flex items-start gap-2.5">
            <MapPin className="w-4 h-4 text-indigo-600 mt-0.5 shrink-0" />
            <div>
              <span className="text-xs text-slate-500 block">Department & Semester</span>
              <span className="font-semibold text-slate-800">
                {allocation.department || "General"}
                {allocation.semester ? ` • ${allocation.semester}` : ""}
              </span>
            </div>
          </div>
        </div>

        {allocation.instructions && (
          <div className="mt-4 bg-amber-50/80 border border-amber-200 rounded-xl p-3.5 flex items-start gap-2.5 text-xs sm:text-sm text-amber-900">
            <Info className="w-4 h-4 text-amber-600 mt-0.5 shrink-0" />
            <div>
              <span className="font-semibold block">Candidate Instructions:</span>
              <p className="mt-0.5 text-amber-800">{allocation.instructions}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
