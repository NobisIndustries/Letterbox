import { useState } from "react";
import type { LetterListItem } from "@/types";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { LetterCard } from "@/components/LetterCard";
import { fetchLetters, fetchLetter, fetchSetting, fetchReceivers, updateTask } from "@/api/client";

const PAGE_SIZE = 20;

function FilterPanel({
  search, setSearch,
  dateFrom, setDateFrom,
  dateTo, setDateTo,
  tag, setTag,
  receiver, setReceiver,
  resetPage,
  compact,
}: {
  search: string; setSearch: (v: string) => void;
  dateFrom: string; setDateFrom: (v: string) => void;
  dateTo: string; setDateTo: (v: string) => void;
  tag: string; setTag: (v: string) => void;
  receiver: string; setReceiver: (v: string) => void;
  resetPage: () => void;
  compact: boolean;
}) {
  const [showExtra, setShowExtra] = useState(false);

  const { data: tagsSetting } = useQuery({
    queryKey: ["settings", "tags"],
    queryFn: () => fetchSetting("tags"),
  });
  const { data: receivers } = useQuery({
    queryKey: ["receivers"],
    queryFn: fetchReceivers,
  });

  const tags = tagsSetting?.value ?? [];
  const inputClass = compact
    ? "bg-muted border-0 focus-visible:ring-1 h-8 text-sm"
    : "bg-muted border-0 focus-visible:ring-1";
  const selectClass = compact
    ? "bg-muted border-0 rounded-md px-2 h-8 text-sm w-full focus:outline-none focus:ring-1 focus:ring-ring"
    : "bg-muted border-0 rounded-md px-2 py-2 text-sm w-full focus:outline-none focus:ring-1 focus:ring-ring";
  const labelClass = "text-xs text-muted-foreground";

  const hasActiveFilters = dateFrom || dateTo || tag || receiver;

  return (
    <div className="flex flex-col gap-2">
      <div className="flex gap-1.5">
        <Input
          placeholder="Search letters..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); resetPage(); }}
          className={inputClass + " flex-1"}
        />
        <button
          onClick={() => setShowExtra((v) => !v)}
          className={`shrink-0 px-2 rounded-md text-xs border transition-colors ${
            hasActiveFilters
              ? "bg-primary text-primary-foreground border-primary"
              : showExtra
              ? "bg-muted text-foreground border-border"
              : "bg-muted text-muted-foreground border-transparent"
          }`}
          aria-label="Toggle filters"
        >
          {hasActiveFilters ? "Filters ●" : "Filters"}
        </button>
      </div>

      {showExtra && (
        <>
          {/* Date range */}
          <div className="flex flex-col gap-1">
            <span className={labelClass}>Date range</span>
            <div className="flex items-center bg-muted rounded-md px-2 gap-1">
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => { setDateFrom(e.target.value); resetPage(); }}
                className="flex-1 min-w-0 bg-transparent text-xs py-1.5 focus:outline-none"
              />
              <span className="text-muted-foreground text-xs shrink-0">–</span>
              <input
                type="date"
                value={dateTo}
                onChange={(e) => { setDateTo(e.target.value); resetPage(); }}
                className="flex-1 min-w-0 bg-transparent text-xs py-1.5 focus:outline-none"
              />
            </div>
          </div>

          {/* Tag filter */}
          {tags.length > 0 && (
            <div className="flex flex-col gap-1">
              <span className={labelClass}>Tag</span>
              <select
                value={tag}
                onChange={(e) => { setTag(e.target.value); resetPage(); }}
                className={selectClass}
              >
                <option value="">All tags</option>
                {tags.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>
          )}

          {/* Receiver filter */}
          {receivers && receivers.length > 0 && (
            <div className="flex flex-col gap-1">
              <span className={labelClass}>Recipient</span>
              <select
                value={receiver}
                onChange={(e) => { setReceiver(e.target.value); resetPage(); }}
                className={selectClass}
              >
                <option value="">All recipients</option>
                {receivers.map((r) => (
                  <option key={r} value={r}>{r}</option>
                ))}
              </select>
            </div>
          )}

          {hasActiveFilters && (
            <button
              onClick={() => { setDateFrom(""); setDateTo(""); setTag(""); setReceiver(""); resetPage(); }}
              className="text-xs text-muted-foreground hover:text-foreground underline text-left"
            >
              Clear filters
            </button>
          )}
        </>
      )}
    </div>
  );
}

function LetterMetaPanel({ letterId }: { letterId: number }) {
  const queryClient = useQueryClient();
  const { data: letter, isLoading } = useQuery({
    queryKey: ["letter", String(letterId)],
    queryFn: () => fetchLetter(letterId),
    enabled: !!letterId,
  });

  const toggleTask = useMutation({
    mutationFn: ({ taskId, isDone }: { taskId: number; isDone: boolean }) =>
      updateTask(taskId, { is_done: isDone }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["letter", String(letterId)] });
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
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
              <div
                key={task.id}
                className="flex items-start gap-2 text-sm cursor-pointer"
                onClick={() => toggleTask.mutate({ taskId: task.id, isDone: !task.is_done })}
              >
                <span className={`mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border text-[10px] transition-colors ${
                  task.is_done ? "bg-primary border-primary text-primary-foreground" : "border-muted-foreground text-transparent"
                }`}>✓</span>
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
  const [tag, setTag] = useState("");
  const [receiver, setReceiver] = useState("");
  const [page, setPage] = useState(0);
  const [selectedLetterId, setSelectedLetterId] = useState<number | null>(null);

  const resetPage = () => setPage(0);

  const activeSearch = search.length >= 3 ? search : "";

  const { data, isLoading } = useQuery({
    queryKey: ["letters", activeSearch, dateFrom, dateTo, tag, receiver, page],
    queryFn: () =>
      fetchLetters({
        q: activeSearch || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        tag: tag || undefined,
        receiver: receiver || undefined,
        offset: page * PAGE_SIZE,
        limit: PAGE_SIZE,
      }),
  });

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  const monthLabel = (dateStr: string) => {
    const d = new Date(dateStr + "T00:00:00");
    return d.toLocaleString("default", { month: "long", year: "numeric" });
  };

  const renderLetterList = (items: LetterListItem[], onSelect: (id: number) => void, withSelected = false) => {
    let lastMonth = "";
    return items.map((letter) => {
      const month = letter.creation_date ? monthLabel(letter.creation_date) : "";
      const showDivider = month && month !== lastMonth;
      if (showDivider) lastMonth = month;
      return (
        <div key={letter.id}>
          {showDivider && (
            <div className="flex items-center gap-2 px-1 pt-2 pb-1">
              <div className="flex-1 h-px bg-primary/20" />
              <span className="text-[10px] font-medium text-primary/60 uppercase tracking-widest shrink-0">{month}</span>
              <div className="flex-1 h-px bg-primary/20" />
            </div>
          )}
          <LetterCard
            letter={letter}
            selected={withSelected && selectedLetterId === letter.id}
            onSelect={onSelect}
          />
        </div>
      );
    });
  };

  const handleSelect = (id: number) => {
    setSelectedLetterId(id);
  };

  const handleMobileSelect = (id: number) => {
    navigate(`/letters/${id}`);
  };

  const filterProps = {
    search, setSearch,
    dateFrom, setDateFrom,
    dateTo, setDateTo,
    tag, setTag,
    receiver, setReceiver,
    resetPage,
  };

  return (
    <>
      {/* Mobile layout */}
      <div className="md:hidden flex flex-col gap-3 p-4">
        <h1 className="text-lg font-semibold">Archive</h1>
        <FilterPanel {...filterProps} compact={false} />
        {isLoading && (
          <p className="text-center text-sm text-muted-foreground py-8">Loading...</p>
        )}
        {data && data.items.length === 0 && (
          <p className="text-center text-sm text-muted-foreground py-8">No letters found</p>
        )}
        <div className="flex flex-col gap-2">
          {data && renderLetterList(data.items, handleMobileSelect)}
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
        <div className="w-80 shrink-0 flex flex-col border-r bg-card overflow-hidden">
          <div className="flex flex-col gap-2 p-3 border-b">
            <h1 className="text-base font-semibold">Archive</h1>
            <FilterPanel {...filterProps} compact={true} />
          </div>

          <div className="flex-1 overflow-y-auto p-2 flex flex-col gap-1">
            {isLoading && (
              <p className="text-center text-sm text-muted-foreground py-8">Loading...</p>
            )}
            {data && data.items.length === 0 && (
              <p className="text-center text-sm text-muted-foreground py-8">No letters found</p>
            )}
            {data && renderLetterList(data.items, handleSelect, true)}
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
        <div className="w-[28rem] shrink-0 border-r overflow-hidden bg-background">
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
