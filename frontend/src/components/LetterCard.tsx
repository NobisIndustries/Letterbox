import { Link } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { LetterListItem } from "@/types";

export function LetterCard({ letter }: { letter: LetterListItem }) {
  return (
    <Link to={`/letters/${letter.id}`}>
      <Card className="hover:bg-muted/50 transition-colors">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium leading-tight">
            {letter.title || "Untitled"}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-1 text-xs text-muted-foreground">
          {letter.sender && <p>From: {letter.sender}</p>}
          {letter.receiver && <p>To: {letter.receiver}</p>}
          {letter.creation_date && <p>Date: {letter.creation_date}</p>}
          {letter.tags && (
            <div className="flex flex-wrap gap-1 pt-1">
              {letter.tags.split(", ").map((tag) => (
                <Badge key={tag} variant="secondary" className="text-[10px]">
                  {tag}
                </Badge>
              ))}
            </div>
          )}
          {letter.summary && (
            <p className="line-clamp-2 pt-1">{letter.summary}</p>
          )}
        </CardContent>
      </Card>
    </Link>
  );
}
