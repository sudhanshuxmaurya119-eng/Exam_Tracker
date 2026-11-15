import React from "react";
import { AlertTriangle, CheckCircle2, Info, WifiOff } from "lucide-react";

interface StatusBannerProps {
  type: "error" | "connection-error" | "success" | "info";
  title?: string;
  message: string;
  onDismiss?: () => void;
}

export const StatusBanner: React.FC<StatusBannerProps> = ({
  type,
  title,
  message,
  onDismiss,
}) => {
  const styles = {
    error: "bg-rose-50 border-rose-200 text-rose-900",
    "connection-error": "bg-rose-950 border-rose-800 text-rose-100",
    success: "bg-emerald-50 border-emerald-200 text-emerald-900",
    info: "bg-indigo-50 border-indigo-200 text-indigo-900",
  }[type];

  const Icon = {
    error: AlertTriangle,
    "connection-error": WifiOff,
    success: CheckCircle2,
    info: Info,
  }[type];

  return (
    <div className={`rounded-xl border p-4 flex items-start justify-between gap-3 ${styles}`}>
      <div className="flex items-start gap-3">
        <Icon className="w-5 h-5 mt-0.5 shrink-0" />
        <div>
          {title && <h4 className="font-semibold text-sm">{title}</h4>}
          <p className="text-sm mt-0.5">{message}</p>
        </div>
      </div>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          className="text-xs font-semibold underline opacity-80 hover:opacity-100"
        >
          Dismiss
        </button>
      )}
    </div>
  );
};
