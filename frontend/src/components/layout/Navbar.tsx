import { Link, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import { MapPin, BarChart3, Download, Shield, Plus, Sun, Moon } from "lucide-react";
import { useDarkMode } from "../../context/DarkModeContext";

const NAV_ITEMS = [
  { to: "/", label: "Map", icon: MapPin },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/downloads", label: "Downloads", icon: Download },
  { to: "/admin", label: "Admin", icon: Shield },
];

export default function Navbar() {
  const location = useLocation();
  const { dark, toggle } = useDarkMode();
  const [isAdminLoggedIn, setIsAdminLoggedIn] = useState(
    () => !!localStorage.getItem("gvp_admin_token")
  );

  useEffect(() => {
    const syncAdminState = () => setIsAdminLoggedIn(!!localStorage.getItem("gvp_admin_token"));
    window.addEventListener("storage", syncAdminState);
    window.addEventListener("gvp-admin-auth-changed", syncAdminState);
    return () => {
      window.removeEventListener("storage", syncAdminState);
      window.removeEventListener("gvp-admin-auth-changed", syncAdminState);
    };
  }, []);

  return (
    <nav className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 sticky top-0 z-50 transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-14">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-8 h-8 bg-red-500 rounded-lg flex items-center justify-center">
              <MapPin size={18} className="text-white" />
            </div>
            <span className="font-bold text-gray-900 dark:text-white text-lg hidden sm:block">
              GVP Watch
            </span>
          </Link>

          <div className="hidden md:flex items-center gap-1">
            {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
              <Link
                key={to}
                to={to}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors flex items-center gap-1.5 ${
                  location.pathname === to
                    ? "bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white"
                    : "text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white hover:bg-gray-50 dark:hover:bg-gray-800"
                }`}
              >
                <Icon size={16} />
                {label}
              </Link>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={toggle}
              className="p-2 rounded-lg text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
              title={dark ? "Switch to light mode" : "Switch to dark mode"}
            >
              {dark ? <Sun size={18} /> : <Moon size={18} />}
            </button>
            {!isAdminLoggedIn && (
              <Link
                to="/submit"
                className="bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-1.5 transition-colors"
              >
                <Plus size={16} />
                <span className="hidden sm:inline">Report GVP</span>
                <span className="sm:hidden">Report</span>
              </Link>
            )}
          </div>
        </div>
      </div>

      {/* Mobile bottom nav */}
      <div className="md:hidden fixed bottom-0 left-0 right-0 bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-800 z-50 transition-colors">
        <div className="flex justify-around py-2">
          {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
            <Link
              key={to}
              to={to}
              className={`flex flex-col items-center gap-0.5 px-3 py-1 text-xs ${
                location.pathname === to
                  ? "text-red-500"
                  : "text-gray-500 dark:text-gray-400"
              }`}
            >
              <Icon size={18} />
              {label}
            </Link>
          ))}
        </div>
      </div>
    </nav>
  );
}
