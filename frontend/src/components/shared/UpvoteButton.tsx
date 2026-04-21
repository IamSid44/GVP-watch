import { useState } from "react";
import { ThumbsUp } from "lucide-react";
import { upvoteReport } from "../../api/reports";

function getFingerprint(): string {
  let fp = localStorage.getItem("gvp_fp");
  if (!fp) {
    fp = Math.random().toString(36).substring(2) + Date.now().toString(36);
    localStorage.setItem("gvp_fp", fp);
  }
  return fp;
}

export default function UpvoteButton({
  ticketId,
  count,
}: {
  ticketId: string;
  count: number;
}) {
  const [upvotes, setUpvotes] = useState(count);
  const [voted, setVoted] = useState(false);

  const handleUpvote = async () => {
    if (voted) return;
    const fp = getFingerprint();
    const result = await upvoteReport(ticketId, fp);
    setUpvotes(result.upvote_count);
    if (result.success) setVoted(true);
    else setVoted(true); // already voted
  };

  return (
    <button
      onClick={handleUpvote}
      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
        voted
          ? "bg-green-100 text-green-700 cursor-default"
          : "bg-gray-100 text-gray-700 hover:bg-gray-200 cursor-pointer"
      }`}
    >
      <ThumbsUp size={16} />
      {upvotes}
    </button>
  );
}
