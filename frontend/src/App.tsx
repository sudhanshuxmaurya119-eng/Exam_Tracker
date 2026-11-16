import React from "react";
import { BrowserRouter, HashRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { Navbar } from "./components/Navbar";
import { StudentPortal } from "./pages/StudentPortal";
import { AdminLogin } from "./pages/AdminLogin";
import { AdminDashboard } from "./pages/AdminDashboard";
import { Timetable } from "./pages/Timetable";

const Router = import.meta.env.VITE_GITHUB_PAGES === "true" ? HashRouter : BrowserRouter;

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <Router>
        <div className="app-shell min-h-screen flex flex-col">
          <Navbar />
          <div className="flex-1">
            <Routes>
              <Route path="/" element={<StudentPortal />} />
              <Route path="/timetable" element={<Timetable />} />
              <Route path="/admin/login" element={<AdminLogin />} />
              <Route path="/admin/dashboard" element={<AdminDashboard />} />
              <Route path="/admin" element={<Navigate to="/admin/dashboard" replace />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </div>
          <footer className="flex items-center justify-center gap-1 border-t border-stone-200 bg-white/90 px-4 py-6 text-sm text-stone-600">
            <span>Made By</span>{" "}
            <a
              href="https://www.linkedin.com/in/sudhanshu-maurya-b4421b401/"
              target="_blank"
              rel="noopener noreferrer"
              aria-label="Sudhanshu on LinkedIn"
              className="inline-flex items-center gap-2 font-bold text-stone-950 hover:text-[#0A66C2] hover:underline"
            >
              Sudhanshu
              <span aria-hidden="true" className="inline-flex h-8 w-8 items-center justify-center rounded bg-[#0A66C2] text-2xl font-extrabold leading-none tracking-tight text-white">in</span>
            </a>
          </footer>
        </div>
      </Router>
    </AuthProvider>
  );
};

export default App;
