import { Routes, Route } from "react-router-dom";
import { DarkModeProvider } from "./context/DarkModeContext";
import Navbar from "./components/layout/Navbar";
import HomePage from "./pages/HomePage";
import SubmitReportPage from "./pages/SubmitReportPage";
import ReportPage from "./pages/ReportPage";
import WardPage from "./pages/WardPage";
import AnalyticsPage from "./pages/AnalyticsPage";
import DownloadsPage from "./pages/DownloadsPage";
import AdminPage from "./pages/AdminPage";

export default function App() {
  return (
    <DarkModeProvider>
      <div className="min-h-screen flex flex-col bg-white dark:bg-gray-950 text-gray-900 dark:text-gray-100 transition-colors">
        <Navbar />
        <div className="flex-1 flex flex-col">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/submit" element={<SubmitReportPage />} />
            <Route path="/report/:id" element={<ReportPage />} />
            <Route path="/ward/:id" element={<WardPage />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="/downloads" element={<DownloadsPage />} />
            <Route path="/admin" element={<AdminPage />} />
          </Routes>
        </div>
        <footer className="bg-gray-50 dark:bg-gray-900 border-t border-gray-200 dark:border-gray-800 py-2 px-4 text-center text-xs text-gray-500 dark:text-gray-400 hidden md:block">
          The collectors are not paid officially. Please support them by paying the nominal fee.
        </footer>
      </div>
    </DarkModeProvider>
  );
}
