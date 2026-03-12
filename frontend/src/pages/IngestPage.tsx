import { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { uploadImages } from "@/api/client";
import { Camera, FileText, Images, Mail } from "lucide-react";

interface IngestPageProps {
  onJobCreated: (jobId: string) => void;
}

export function IngestPage({ onJobCreated }: IngestPageProps) {
  const cameraRef = useRef<HTMLInputElement>(null);
  const galleryRef = useRef<HTMLInputElement>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [previews, setPreviews] = useState<string[]>([]);
  const [isPdfMode, setIsPdfMode] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [firstCapture, setFirstCapture] = useState<"camera" | "gallery" | null>(null);

  const addFiles = (newFiles: FileList | null, source?: "camera" | "gallery") => {
    if (!newFiles) return;
    const arr = Array.from(newFiles);

    // Handle PDF upload
    const pdfFile = arr.find((f) => f.type === "application/pdf");
    if (pdfFile) {
      setIsPdfMode(true);
      setFiles([pdfFile]);
      setPreviews([]);
      if (!firstCapture && source) setFirstCapture(source);
      return;
    }

    // Image upload (reset PDF mode)
    setIsPdfMode(false);
    setFiles((prev) => [...prev, ...arr]);
    const newPreviews = arr.map((f) => URL.createObjectURL(f));
    setPreviews((prev) => [...prev, ...newPreviews]);
    if (!firstCapture && source) setFirstCapture(source);
  };

  const removeFile = (index: number) => {
    URL.revokeObjectURL(previews[index]);
    setFiles((prev) => prev.filter((_, i) => i !== index));
    setPreviews((prev) => prev.filter((_, i) => i !== index));
  };

  const clearAll = () => {
    previews.forEach((url) => URL.revokeObjectURL(url));
    setFiles([]);
    setPreviews([]);
    setIsPdfMode(false);
    setFirstCapture(null);
  };

  const handleProcess = async () => {
    if (files.length === 0) return;
    setUploading(true);
    try {
      const res = await uploadImages(files);
      onJobCreated(res.job_id);
      clearAll();
    } finally {
      setUploading(false);
    }
  };

  const hasFiles = files.length > 0;

  return (
    <div className="flex flex-col items-center gap-6 p-4 max-w-lg mx-auto min-h-[calc(100dvh-5rem)]">
      {/* Branding */}
      <div className="flex flex-col items-center gap-1 pt-4">
        <div className="flex items-center gap-2">
          <Mail size={28} className="text-primary" />
          <span className="text-2xl font-bold tracking-tight">Letterbox</span>
        </div>
        <p className="text-xs text-muted-foreground tracking-widest uppercase">
          Scan · Extract · Archive
        </p>
      </div>

      {/* Hidden inputs */}
      <input
        ref={cameraRef}
        type="file"
        accept="image/*"
        capture="environment"
        multiple
        className="hidden"
        onChange={(e) => { addFiles(e.target.files, "camera"); e.target.value = ""; }}
      />
      <input
        ref={galleryRef}
        type="file"
        accept="image/*,application/pdf"
        multiple
        className="hidden"
        onChange={(e) => { addFiles(e.target.files, "gallery"); e.target.value = ""; }}
      />

      {/* Capture buttons */}
      {!hasFiles ? (
        <div className="flex flex-col items-center gap-4 w-full min-h-[calc(50dvh-6rem)] justify-end pb-4">
          <div className="flex gap-3">
            <Button
              variant="default"
              className="flex flex-col h-20 w-28 gap-1 text-sm"
              onClick={() => cameraRef.current?.click()}
            >
              <Camera size={24} />
              Camera
            </Button>
            <Button
              variant="outline"
              className="flex flex-col h-20 w-28 gap-1 text-sm"
              onClick={() => galleryRef.current?.click()}
            >
              <Images size={24} />
              Gallery
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">Photograph each page of the letter, or select a PDF</p>
        </div>
      ) : isPdfMode ? (
        <>
          {/* PDF card */}
          <div className="w-full max-w-md">
            <div className="flex items-center gap-3 p-4 rounded-md border bg-muted/40">
              <FileText size={32} className="text-primary shrink-0" />
              <div className="flex flex-col min-w-0">
                <span className="font-medium truncate">{files[0].name}</span>
                <span className="text-xs text-muted-foreground">
                  {(files[0].size / 1024).toFixed(0)} KB
                </span>
              </div>
              <button
                onClick={clearAll}
                className="ml-auto flex h-6 w-6 items-center justify-center rounded-full bg-destructive text-white text-xs shrink-0"
              >
                ×
              </button>
            </div>
          </div>

          {/* Action row */}
          <div className="mt-auto w-full max-w-md flex flex-col gap-2 pb-2">
            <Button
              className="w-full h-14 text-base"
              onClick={handleProcess}
              disabled={uploading}
            >
              {uploading ? "Uploading..." : "Process PDF"}
            </Button>
            <Button
              variant="outline"
              className="w-full h-12 gap-1.5"
              onClick={() => galleryRef.current?.click()}
            >
              <Images size={16} /> Choose different file
            </Button>
          </div>
        </>
      ) : (
        <>
          {/* Image grid */}
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

          {/* Action row — two-column: process left, add-more right */}
          <div className="mt-auto w-full max-w-md flex gap-3 pb-2">
            <Button
              variant="outline"
              className="flex-1 h-28 flex flex-col gap-1 text-sm bg-muted"
              onClick={handleProcess}
              disabled={uploading}
            >
              <FileText size={22} />
              {uploading ? "Uploading..." : "Process"}
              {!uploading && <span className="text-xs opacity-70">{files.length} page{files.length > 1 ? "s" : ""}</span>}
            </Button>
            <div className="flex flex-col gap-2 flex-1">
              <Button
                variant={firstCapture === "camera" ? "default" : "outline"}
                className="flex-1 h-[52px] gap-1.5"
                onClick={() => cameraRef.current?.click()}
              >
                <Camera size={16} /> Camera
              </Button>
              <Button
                variant={firstCapture === "gallery" ? "default" : "outline"}
                className="flex-1 h-[52px] gap-1.5"
                onClick={() => galleryRef.current?.click()}
              >
                <Images size={16} /> Gallery
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
