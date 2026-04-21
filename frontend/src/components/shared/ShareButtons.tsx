import { Share2 } from "lucide-react";

export default function ShareButtons({
  title,
  url,
}: {
  title: string;
  url: string;
}) {
  const encodedUrl = encodeURIComponent(url);
  const encodedTitle = encodeURIComponent(title);

  const share = async () => {
    if (navigator.share) {
      await navigator.share({ title, url });
    }
  };

  return (
    <div className="flex items-center gap-2">
      <a
        href={`https://twitter.com/intent/tweet?text=${encodedTitle}&url=${encodedUrl}`}
        target="_blank"
        rel="noopener noreferrer"
        className="px-3 py-1.5 bg-black text-white rounded-lg text-xs font-medium hover:bg-gray-800"
      >
        X / Twitter
      </a>
      <a
        href={`https://wa.me/?text=${encodedTitle}%20${encodedUrl}`}
        target="_blank"
        rel="noopener noreferrer"
        className="px-3 py-1.5 bg-green-600 text-white rounded-lg text-xs font-medium hover:bg-green-700"
      >
        WhatsApp
      </a>
      {"share" in navigator && (
        <button
          onClick={share}
          className="px-3 py-1.5 bg-gray-100 text-gray-700 rounded-lg text-xs font-medium hover:bg-gray-200 inline-flex items-center gap-1"
        >
          <Share2 size={14} /> Share
        </button>
      )}
    </div>
  );
}
