import { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { uploadImages } from "@/api/client";
import { JobStatusChip } from "@/components/JobStatusChip";

export function IngestPage() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [previews, setPreviews] = useState<string[]>([]);
  const [jobIds, setJobIds] = useState<string[]>([]);
  const [uploading, setUploading] = useState(false);

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
      setJobIds((prev) => [...prev, res.job_id]);
      previews.forEach((url) => URL.revokeObjectURL(url));
      setFiles([]);
      setPreviews([]);
    } finally {
      setUploading(false);
    }
  };

  const dismissJob = (jobId: string) => {
    setJobIds((prev) => prev.filter((id) => id !== jobId));
  };

  return (
    <div className="flex flex-col items-center gap-4 p-4 max-w-lg mx-auto">
      <h1 className="text-lg font-semibold">Scan Letter</h1>

      {jobIds.length > 0 && (
        <div className="flex flex-wrap gap-2 w-full max-w-md">
          {jobIds.map((id) => (
            <JobStatusChip key={id} jobId={id} onDismiss={() => dismissJob(id)} />
          ))}
        </div>
      )}

      <input
        ref={inputRef}
        type="file"
        accept="image/*"
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
          <Button onClick={handleProcess} disabled={uploading}>
            {uploading
              ? "Uploading..."
              : `Process ${files.length} page${files.length > 1 ? "s" : ""}`}
          </Button>
        </div>
      )}
    </div>
  );
}
