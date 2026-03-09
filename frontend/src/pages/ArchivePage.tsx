import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { LetterCard } from "@/components/LetterCard";
import { fetchLetters } from "@/api/client";

const PAGE_SIZE = 20;

export function ArchivePage() {
  const [search, setSearch] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [page, setPage] = useState(0);

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

  return (
    <div className="flex flex-col gap-3 p-4">
      <h1 className="text-lg font-semibold">Archive</h1>

      <Input
        placeholder="Search letters..."
        value={search}
        onChange={(e) => {
          setSearch(e.target.value);
          setPage(0);
        }}
      />

      <div className="flex gap-2">
        <Input
          type="date"
          value={dateFrom}
          onChange={(e) => {
            setDateFrom(e.target.value);
            setPage(0);
          }}
          className="flex-1"
        />
        <Input
          type="date"
          value={dateTo}
          onChange={(e) => {
            setDateTo(e.target.value);
            setPage(0);
          }}
          className="flex-1"
        />
      </div>

      {isLoading && (
        <p className="text-center text-sm text-muted-foreground py-8">
          Loading...
        </p>
      )}

      {data && data.items.length === 0 && (
        <p className="text-center text-sm text-muted-foreground py-8">
          No letters found
        </p>
      )}

      <div className="flex flex-col gap-2">
        {data?.items.map((letter) => (
          <LetterCard key={letter.id} letter={letter} />
        ))}
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 pt-2">
          <Button
            variant="outline"
            size="sm"
            disabled={page === 0}
            onClick={() => setPage((p) => p - 1)}
          >
            Prev
          </Button>
          <span className="text-sm text-muted-foreground">
            {page + 1} / {totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={page >= totalPages - 1}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  );
}
