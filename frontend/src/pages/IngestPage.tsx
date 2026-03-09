import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { uploadImages } from "@/api/client";
import { useSSE } from "@/hooks/useSSE";

const STATUS_LABELS: Record<string, string> = {
  queued: "Waiting in queue...",
  processing: "Processing...",
  enhancing: "Enhancing images...",
  extracting: "Extracting text & metadata...",
  saving: "Saving PDF & data...",
  done: "Done!",
  error: "Processing failed",
};

export function IngestPage() {
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [previews, setPreviews] = useState<string[]>([]);
  const [jobId, setJobId] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const status = useSSE(jobId);

  const addFiles = (newFiles: FileList | null) => {
    if (!newFiles) return;
    const arr = Array.from(newFiles);
    setFiles((prev) => [...prev, ...arr]);
    const newPreviews = arr.map((f) => URL.createObjectURL(f));
    setPreviews((prev) => [...prev, ...newPreviews]);
  };

  const removeFile = (index: number) => {
    URL.revokeObjectURL(previews[index]);
    setFiles((prev) => prev.filter((_, i) => i !== index));
    setPreviews((prev) => prev.filter((_, i) => i !== index));
  };

  const handleProcess = async () => {
    if (files.length === 0) return;
    setUploading(true);
    try {
      const res = await uploadImages(files);
      setJobId(res.job_id);
    } catch {
      setUploading(false);
    }
  };

  // Navigate to letter detail when done
  if (status?.status === "done" && status.letter_id) {
    navigate(`/letters/${status.letter_id}`);
  }

  const processing = uploading || !!jobId;
  const statusText = status ? STATUS_LABELS[status.status] ?? status.status : null;

  return (
    <div className="flex flex-col items-center gap-4 p-4">
      <h1 className="text-lg font-semibold">Scan Letter</h1>

      {!processing && (
        <>
          <input
            ref={inputRef}
            type="file"
            accept="image/*"
            capture="environment"
            multiple
            className="hidden"
            onChange={(e) => addFiles(e.target.files)}
          />

          <Button
            size="lg"
            className="h-20 w-20 rounded-full text-3xl"
            onClick={() => inputRef.current?.click()}
          >
            +
          </Button>
          <p className="text-sm text-muted-foreground">
            Tap to take a photo or select images
          </p>

          {previews.length > 0 && (
            <div className="grid grid-cols-3 gap-2 w-full max-w-md">
              {previews.map((url, i) => (
                <div key={i} className="relative">
                  <img
                    src={url}
                    alt={`Page ${i + 1}`}
                    className="w-full aspect-[3/4] object-cover rounded-md border"
                  />
                  <button
                    onClick={() => removeFile(i)}
                    className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-destructive text-white text-xs"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}

          {files.length > 0 && (
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => inputRef.current?.click()}>
                Add Page
              </Button>
              <Button onClick={handleProcess}>
                Process {files.length} page{files.length > 1 ? "s" : ""}
              </Button>
            </div>
          )}
        </>
      )}

      {processing && (
        <Card className="w-full max-w-md">
          <CardContent className="flex flex-col items-center gap-3 py-8">
            {status?.status === "error" ? (
              <>
                <p className="text-destructive font-medium">{statusText}</p>
                <Button
                  variant="outline"
                  onClick={() => {
                    setJobId(null);
                    setUploading(false);
                  }}
                >
                  Try Again
                </Button>
              </>
            ) : (
              <>
                <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
                <p className="text-sm text-muted-foreground">
                  {statusText ?? "Uploading..."}
                </p>
              </>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
