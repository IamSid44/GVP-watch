import { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Camera, MapPin, Loader2, Upload } from "lucide-react";
import { submitReport } from "../../api/reports";
import { CATEGORY_LABELS } from "../../types";

export default function ReportForm() {
  const navigate = useNavigate();
  const fileRef = useRef<HTMLInputElement>(null);
  const [photo, setPhoto] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [lat, setLat] = useState<number | null>(null);
  const [lng, setLng] = useState<number | null>(null);
  const [severity, setSeverity] = useState("MEDIUM");
  const [category, setCategory] = useState("garbage_on_roads");
  const [description, setDescription] = useState("");
  const [name, setName] = useState("");
  const [address, setAddress] = useState("");
  const [loading, setLoading] = useState(false);
  const [geoLoading, setGeoLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handlePhoto = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setPhoto(file);
    setPreview(URL.createObjectURL(file));
  };

  const detectLocation = () => {
    if (!navigator.geolocation) {
      setError("Geolocation not supported");
      return;
    }
    setGeoLoading(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLat(pos.coords.latitude);
        setLng(pos.coords.longitude);
        setGeoLoading(false);
      },
      () => {
        setError("Could not detect location. Please allow location access.");
        setGeoLoading(false);
      },
      { enableHighAccuracy: true }
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!lat || !lng) {
      setError("Please detect your location first");
      return;
    }
    setLoading(true);
    setError(null);

    const formData = new FormData();
    formData.append("latitude", lat.toString());
    formData.append("longitude", lng.toString());
    formData.append("severity", severity);
    formData.append("category", category);
    if (description) formData.append("description", description);
    if (name) formData.append("reporter_name", name);
    if (address) formData.append("address", address);
    if (photo) formData.append("photo", photo);

    try {
      const report = await submitReport(formData);
      navigate(`/report/${report.ticket_id}`);
    } catch {
      setError("Failed to submit report. Please try again.");
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Photo */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Photo of the issue
        </label>
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          capture="environment"
          onChange={handlePhoto}
          className="hidden"
        />
        {preview ? (
          <div className="relative">
            <img
              src={preview}
              alt="Preview"
              className="w-full h-48 object-cover rounded-xl"
            />
            <button
              type="button"
              onClick={() => fileRef.current?.click()}
              className="absolute bottom-2 right-2 bg-white/90 px-3 py-1 rounded-lg text-sm"
            >
              Change
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            className="w-full h-48 border-2 border-dashed border-gray-300 rounded-xl flex flex-col items-center justify-center gap-2 text-gray-500 hover:border-gray-400 hover:bg-gray-50 transition-colors"
          >
            <Camera size={32} />
            <span className="text-sm">Take photo or upload</span>
          </button>
        )}
      </div>

      {/* Location */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Location
        </label>
        {lat && lng ? (
          <div className="flex items-center gap-2 p-3 bg-green-50 rounded-lg text-green-700 text-sm">
            <MapPin size={16} />
            {lat.toFixed(5)}, {lng.toFixed(5)}
            <button
              type="button"
              onClick={detectLocation}
              className="ml-auto text-green-600 underline text-xs"
            >
              Re-detect
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={detectLocation}
            disabled={geoLoading}
            className="w-full p-3 border border-gray-300 rounded-lg text-sm flex items-center justify-center gap-2 hover:bg-gray-50"
          >
            {geoLoading ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <MapPin size={16} />
            )}
            {geoLoading ? "Detecting..." : "Detect my location"}
          </button>
        )}
      </div>

      {/* Category */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Category
        </label>
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="w-full p-2.5 border border-gray-300 rounded-lg text-sm"
        >
          {Object.entries(CATEGORY_LABELS).map(([k, v]) => (
            <option key={k} value={k}>
              {v}
            </option>
          ))}
        </select>
      </div>

      {/* Severity */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Severity
        </label>
        <div className="grid grid-cols-3 gap-2">
          {[
            { value: "LOW", label: "Minor", color: "bg-amber-500" },
            { value: "MEDIUM", label: "Moderate", color: "bg-orange-500" },
            { value: "HIGH", label: "Severe", color: "bg-red-500" },
          ].map((s) => (
            <button
              key={s.value}
              type="button"
              onClick={() => setSeverity(s.value)}
              className={`p-2.5 rounded-lg text-sm font-medium border-2 transition-colors ${
                severity === s.value
                  ? `${s.color} text-white border-transparent`
                  : "border-gray-200 text-gray-600 hover:border-gray-300"
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {/* Description */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Description (optional)
        </label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={3}
          className="w-full p-2.5 border border-gray-300 rounded-lg text-sm resize-none"
          placeholder="Describe the issue..."
        />
      </div>

      {/* Address */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Address / Landmark (optional)
        </label>
        <input
          type="text"
          value={address}
          onChange={(e) => setAddress(e.target.value)}
          className="w-full p-2.5 border border-gray-300 rounded-lg text-sm"
          placeholder="e.g., Near Gachibowli Stadium"
        />
      </div>

      {/* Name */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Your name (optional)
        </label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="w-full p-2.5 border border-gray-300 rounded-lg text-sm"
          placeholder="Anonymous if left blank"
        />
      </div>

      {error && (
        <div className="p-3 bg-red-50 text-red-700 rounded-lg text-sm">
          {error}
        </div>
      )}

      <button
        type="submit"
        disabled={loading}
        className="w-full bg-red-500 hover:bg-red-600 text-white py-3 rounded-xl text-sm font-medium flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
      >
        {loading ? (
          <Loader2 size={18} className="animate-spin" />
        ) : (
          <Upload size={18} />
        )}
        {loading ? "Submitting..." : "Submit Report"}
      </button>
    </form>
  );
}
