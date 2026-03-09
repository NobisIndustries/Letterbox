import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { LetterCard } from "@/components/LetterCard";
import { fetchLetters, fetchLetter } from "@/api/client";

const PAGE_SIZE = 20;

function LetterMetaPanel({ letterId }: { letterId: number }) {
  const { data: letter, isLoading } = useQuery({
    queryKey: ["letter", String(letterId)],
    queryFn: () => fetchLetter(letterId),
    enabled: !!letterId,
  });

  if (isLoading) {
    return <p className="p-4 text-sm text-muted-foreground">Loading...</p>;
  }
  if (!letter) return null;

  return (
    <div className="flex flex-col gap-4 p-4 overflow-y-auto h-full">
      <h2 className="text-base font-semibold leading-tight">{letter.title || "Untitled"}</h2>

      <div className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
        {letter.sender && (
          <>
            <span className="text-muted-foreground">From</span>
            <span>{letter.sender}</span>
          </>
        )}
        {letter.receiver && (
          <>
            <span className="text-muted-foreground">To</span>
            <span>{letter.receiver}</span>
          </>
        )}
        {letter.creation_date && (
          <>
            <span className="text-muted-foreground">Date</span>
            <span>{letter.creation_date}</span>
          </>
        )}
      </div>

      {letter.tags && (
        <div className="flex flex-wrap gap-1">
          {letter.tags.split(", ").map((tag) => (
            <span
              key={tag}
              className="text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary font-medium"
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      {letter.summary && (
        <div className="rounded-lg bg-muted/60 p-3 text-sm">
          {letter.summary}
        </div>
      )}

      {letter.tasks.length > 0 && (
        <div>
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">Tasks</p>
          <div className="flex flex-col gap-1">
            {letter.tasks.map((task) => (
              <div key={task.id} className="flex items-start gap-2 text-sm">
                <span className={`mt-0.5 ${task.is_done ? "text-primary" : "text-muted-foreground"}`}>
                  {task.is_done ? "✓" : "○"}
                </span>
                <span className={task.is_done ? "line-through opacity-50" : ""}>
                  {task.description}
                  {task.deadline && (
                    <span className="ml-1 text-xs text-muted-foreground">(due {task.deadline})</span>
                  )}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <Button
        variant="outline"
        size="sm"
        onClick={() => window.open(`/letters/${letter.id}`, "_blank")}
        className="mt-auto"
      >
        Open full detail →
      </Button>
    </div>
  );
}

function PdfPanel({ letterId }: { letterId: number }) {
  const { data: letter } = useQuery({
    queryKey: ["letter", String(letterId)],
    queryFn: () => fetchLetter(letterId),
    enabled: !!letterId,
  });

  if (!letter?.pdf_path) {
    return (
      <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
        No PDF available
      </div>
    );
  }

  return (
    <iframe
      src={`/api/letters/${letterId}/pdf`}
      className="w-full h-full rounded-lg"
      title="Letter PDF"
    />
  );
}

export function ArchivePage() {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [page, setPage] = useState(0);
  const [selectedLetterId, setSelectedLetterId] = useState<number | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["letters", search, dateFrom, dateTo, page],
    queryFn: () =>
      fetchLetters({
        q: search || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        offset: page * PAGE_SIZE,
        limit: PAGE_SIZE,
      }),
  });

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  const handleSelect = (id: number) => {
    // On desktop: select in place; mobile: navigate
    setSelectedLetterId(id);
  };

  const handleMobileSelect = (id: number) => {
    navigate(`/letters/${id}`);
  };

  return (
    <>
      {/* Mobile layout */}
      <div className="md:hidden flex flex-col gap-3 p-4">
        <h1 className="text-lg font-semibold">Archive</h1>
        <Input
          placeholder="Search letters..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(0); }}
          className="bg-muted border-0 focus-visible:ring-1"
        />
        <div className="flex gap-2">
          <Input
            type="date"
            value={dateFrom}
            onChange={(e) => { setDateFrom(e.target.value); setPage(0); }}
            className="flex-1 bg-muted border-0 focus-visible:ring-1"
          />
          <Input
            type="date"
            value={dateTo}
            onChange={(e) => { setDateTo(e.target.value); setPage(0); }}
            className="flex-1 bg-muted border-0 focus-visible:ring-1"
          />
        </div>
        {isLoading && (
          <p className="text-center text-sm text-muted-foreground py-8">Loading...</p>
        )}
        {data && data.items.length === 0 && (
          <p className="text-center text-sm text-muted-foreground py-8">No letters found</p>
        )}
        <div className="flex flex-col gap-2">
          {data?.items.map((letter) => (
            <LetterCard
              key={letter.id}
              letter={letter}
              onSelect={handleMobileSelect}
            />
          ))}
        </div>
        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-2 pt-2">
            <Button variant="outline" size="sm" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
              Prev
            </Button>
            <span className="text-sm text-muted-foreground">{page + 1} / {totalPages}</span>
            <Button variant="outline" size="sm" disabled={page >= totalPages - 1} onClick={() => setPage((p) => p + 1)}>
              Next
            </Button>
          </div>
        )}
      </div>

      {/* Desktop 3-pane layout */}
      <div className="hidden md:flex h-screen overflow-hidden">
        {/* Left pane: search + letter list */}
        <div className="w-72 shrink-0 flex flex-col border-r bg-card overflow-hidden">
          <div className="flex flex-col gap-2 p-3 border-b">
            <h1 className="text-base font-semibold">Archive</h1>
            <Input
              placeholder="Search..."
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(0); }}
              className="bg-muted border-0 focus-visible:ring-1 h-8 text-sm"
            />
            <div className="flex gap-1.5">
              <Input
                type="date"
                value={dateFrom}
                onChange={(e) => { setDateFrom(e.target.value); setPage(0); }}
                className="flex-1 bg-muted border-0 focus-visible:ring-1 h-7 text-xs"
              />
              <Input
                type="date"
                value={dateTo}
                onChange={(e) => { setDateTo(e.target.value); setPage(0); }}
                className="flex-1 bg-muted border-0 focus-visible:ring-1 h-7 text-xs"
              />
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-2 flex flex-col gap-1">
            {isLoading && (
              <p className="text-center text-sm text-muted-foreground py-8">Loading...</p>
            )}
            {data && data.items.length === 0 && (
              <p className="text-center text-sm text-muted-foreground py-8">No letters found</p>
            )}
            {data?.items.map((letter) => (
              <LetterCard
                key={letter.id}
                letter={letter}
                selected={selectedLetterId === letter.id}
                onSelect={handleSelect}
              />
            ))}
          </div>

          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 p-2 border-t">
              <Button variant="outline" size="sm" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
                Prev
              </Button>
              <span className="text-xs text-muted-foreground">{page + 1} / {totalPages}</span>
              <Button variant="outline" size="sm" disabled={page >= totalPages - 1} onClick={() => setPage((p) => p + 1)}>
                Next
              </Button>
            </div>
          )}
        </div>

        {/* Middle pane: letter metadata */}
        <div className="w-80 shrink-0 border-r overflow-hidden bg-background">
          {selectedLetterId ? (
            <LetterMetaPanel letterId={selectedLetterId} />
          ) : (
            <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
              Select a letter
            </div>
          )}
        </div>

        {/* Right pane: PDF */}
        <div className="flex-1 overflow-hidden p-4 bg-muted/30">
          {selectedLetterId ? (
            <PdfPanel letterId={selectedLetterId} />
          ) : (
            <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
              No letter selected
            </div>
          )}
        </div>
      </div>
    </>
  );
}
