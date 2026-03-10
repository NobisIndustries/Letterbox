import { useNavigate } from "react-router-dom";
import type { LetterListItem } from "@/types";

interface LetterCardProps {
  letter: LetterListItem;
  selected?: boolean;
  onSelect?: (id: number) => void;
  sortOrder?: "creation_date" | "ingested_at";
}

export function LetterCard({ letter, selected, onSelect, sortOrder = "creation_date" }: LetterCardProps) {
  const navigate = useNavigate();

  const handleClick = (e: React.MouseEvent) => {
    if (onSelect) {
      e.preventDefault();
      onSelect(letter.id);
    } else {
      navigate(`/letters/${letter.id}`);
    }
  };

  return (
    <div
      onClick={handleClick}
      className={`cursor-pointer rounded-xl px-4 py-3 transition-colors ${
        selected
          ? "bg-accent/60"
          : "bg-card hover:bg-muted/60 shadow-sm"
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium leading-tight truncate">
            {letter.sender || <span className="text-muted-foreground italic">Unknown sender</span>}
          </p>
          <p className="text-xs text-muted-foreground leading-tight mt-0.5 truncate">
            → {letter.receiver || "Unknown recipient"}
          </p>
        </div>
        {sortOrder === "ingested_at" ? (
          <span className="text-xs text-muted-foreground shrink-0">
            {new Date(letter.ingested_at).toLocaleDateString()}
          </span>
        ) : letter.creation_date ? (
          <span className="text-xs text-muted-foreground shrink-0">
            {new Date(letter.creation_date + "T00:00:00").toLocaleDateString()}
          </span>
        ) : null}
      </div>
      {letter.title && (
        <p className="text-xs text-muted-foreground truncate mt-1 italic">{letter.title}</p>
      )}
      {letter.summary && (
        <p className="text-xs text-muted-foreground line-clamp-2 mt-1.5">{letter.summary}</p>
      )}
      {letter.tags && (
        <div className="flex flex-wrap gap-1 mt-2">
          {letter.tags.split(", ").map((tag) => (
            <span
              key={tag}
              className="text-[10px] px-1.5 py-0.5 rounded-full bg-primary/10 text-primary font-medium"
            >
              {tag}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
