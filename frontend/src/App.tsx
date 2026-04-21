import { Routes, Route } from "react-router-dom";
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
    <>
      <Navbar />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/submit" element={<SubmitReportPage />} />
        <Route path="/report/:id" element={<ReportPage />} />
        <Route path="/ward/:id" element={<WardPage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
        <Route path="/downloads" element={<DownloadsPage />} />
        <Route path="/admin" element={<AdminPage />} />
      </Routes>
    </>
  );
}
