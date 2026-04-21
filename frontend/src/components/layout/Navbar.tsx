import { Link, useLocation } from "react-router-dom";
import { MapPin, BarChart3, Download, Shield, Plus } from "lucide-react";

const NAV_ITEMS = [
  { to: "/", label: "Map", icon: MapPin },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/downloads", label: "Downloads", icon: Download },
  { to: "/admin", label: "Admin", icon: Shield },
];

export default function Navbar() {
  const location = useLocation();

  return (
    <nav className="bg-white border-b border-gray-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-14">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-8 h-8 bg-red-500 rounded-lg flex items-center justify-center">
              <MapPin size={18} className="text-white" />
            </div>
            <span className="font-bold text-gray-900 text-lg hidden sm:block">
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
                    ? "bg-gray-100 text-gray-900"
                    : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
                }`}
              >
                <Icon size={16} />
                {label}
              </Link>
            ))}
          </div>

          <Link
            to="/submit"
            className="bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-1.5 transition-colors"
          >
            <Plus size={16} />
            <span className="hidden sm:inline">Report GVP</span>
            <span className="sm:hidden">Report</span>
          </Link>
        </div>
      </div>

      {/* Mobile bottom nav */}
      <div className="md:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 z-50">
        <div className="flex justify-around py-2">
          {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
            <Link
              key={to}
              to={to}
              className={`flex flex-col items-center gap-0.5 px-3 py-1 text-xs ${
                location.pathname === to
                  ? "text-red-500"
                  : "text-gray-500"
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
