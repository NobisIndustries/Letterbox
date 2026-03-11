import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { fetchOpenRouterCredits, fetchSetting, updateSetting } from "@/api/client";
import { cn } from "@/lib/utils";
import { type DateFormat, getDateFormat, setDateFormat } from "@/lib/dateFormat";

function SettingList({ settingKey, label, description }: { settingKey: string; label: string; description?: string }) {
  const queryClient = useQueryClient();
  const [newItem, setNewItem] = useState("");

  const { data } = useQuery({
    queryKey: ["settings", settingKey],
    queryFn: () => fetchSetting(settingKey),
  });

  const mutation = useMutation({
    mutationFn: (value: string[]) => updateSetting(settingKey, value),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["settings", settingKey] }),
  });

  const items = data?.value ?? [];

  const addItem = () => {
    const trimmed = newItem.trim();
    if (!trimmed || items.includes(trimmed)) return;
    mutation.mutate([...items, trimmed]);
    setNewItem("");
  };

  const removeItem = (item: string) => {
    mutation.mutate(items.filter((i) => i !== item));
  };

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">{label}</CardTitle>
        {description && (
          <p className="text-xs text-muted-foreground">{description}</p>
        )}
      </CardHeader>
      <CardContent className="space-y-2">
        <div className="flex flex-wrap gap-1">
          {items.map((item) => (
            <Badge
              key={item}
              variant="secondary"
              className="cursor-pointer"
              onClick={() => removeItem(item)}
            >
              {item} ×
            </Badge>
          ))}
          {items.length === 0 && (
            <p className="text-xs text-muted-foreground">None configured</p>
          )}
        </div>
        <div className="flex gap-2">
          <Input
            value={newItem}
            onChange={(e) => setNewItem(e.target.value)}
            placeholder={`Add ${label.toLowerCase().slice(0, -1)}...`}
            onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addItem())}
            className="flex-1"
          />
          <Button size="sm" onClick={addItem} disabled={!newItem.trim()}>
            Add
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function OpenRouterCredits() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["openrouter-credits"],
    queryFn: fetchOpenRouterCredits,
    staleTime: 60_000,
  });

  let body: React.ReactNode;
  if (isLoading) {
    body = <p className="text-xs text-muted-foreground">Loading…</p>;
  } else if (isError || !data) {
    body = <p className="text-xs text-muted-foreground">Could not load credits.</p>;
  } else if (data.is_free_tier) {
    body = <p className="text-xs text-muted-foreground">Free tier — no credit limit.</p>;
  } else {
    const used = data.usage ?? 0;
    const limit = data.limit;
    const remaining = limit != null ? limit - used : null;
    body = (
      <div className="text-sm space-y-0.5">
        {remaining != null && (
          <p>Remaining: <span className="font-medium">${remaining.toFixed(4)}</span></p>
        )}
        <p className="text-xs text-muted-foreground">Used: ${used.toFixed(4)}{limit != null ? ` / $${limit.toFixed(2)}` : ""}</p>
        {data.label && <p className="text-xs text-muted-foreground">Key: {data.label}</p>}
      </div>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">OpenRouter Credits</CardTitle>
        <p className="text-xs text-muted-foreground">Current usage for the configured API key.</p>
      </CardHeader>
      <CardContent>{body}</CardContent>
    </Card>
  );
}

function DewarpingMethodToggle() {
  const queryClient = useQueryClient();

  const { data } = useQuery({
    queryKey: ["settings", "dewarping_method"],
    queryFn: () => fetchSetting("dewarping_method"),
  });

  const mutation = useMutation({
    mutationFn: (value: string[]) => updateSetting("dewarping_method", value),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["settings", "dewarping_method"] }),
  });

  const current = data?.value?.[0] ?? "deep_learning";

  const options = [
    { value: "deep_learning", label: "Deep Learning", desc: "Neural network dewarping (slower, handles complex distortions)" },
    { value: "classic", label: "Classic", desc: "Perspective correction via 4-corner detection (faster, less precise)" },
  ];

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">Dewarping Method</CardTitle>
        <p className="text-xs text-muted-foreground">
          How scanned letter images are straightened and corrected before OCR.
        </p>
      </CardHeader>
      <CardContent className="space-y-2">
        {options.map((opt) => (
          <button
            key={opt.value}
            onClick={() => mutation.mutate([opt.value])}
            className={cn(
              "w-full text-left rounded-md border p-3 transition-colors",
              current === opt.value
                ? "border-primary bg-primary/5"
                : "border-border hover:border-muted-foreground/50"
            )}
          >
            <div className="text-sm font-medium">{opt.label}</div>
            <div className="text-xs text-muted-foreground">{opt.desc}</div>
          </button>
        ))}
      </CardContent>
    </Card>
  );
}

function DateFormatToggle() {
  const [current, setCurrent] = useState<DateFormat>(getDateFormat);

  const options: { value: DateFormat; label: string; desc: string }[] = [
    { value: "auto", label: "Auto", desc: "System locale (varies by device)" },
    { value: "de", label: "European (DD.MM.YYYY)", desc: "e.g. 31.12.2024" },
    { value: "iso", label: "ISO 8601 (YYYY-MM-DD)", desc: "e.g. 2024-12-31" },
    { value: "us", label: "US (MM/DD/YYYY)", desc: "e.g. 12/31/2024" },
  ];

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">Date Format</CardTitle>
        <p className="text-xs text-muted-foreground">
          How dates are displayed throughout the app. Stored locally on this device.
        </p>
      </CardHeader>
      <CardContent className="space-y-2">
        {options.map((opt) => (
          <button
            key={opt.value}
            onClick={() => { setDateFormat(opt.value); setCurrent(opt.value); }}
            className={cn(
              "w-full text-left rounded-md border p-3 transition-colors",
              current === opt.value
                ? "border-primary bg-primary/5"
                : "border-border hover:border-muted-foreground/50"
            )}
          >
            <div className="text-sm font-medium">{opt.label}</div>
            <div className="text-xs text-muted-foreground">{opt.desc}</div>
          </button>
        ))}
      </CardContent>
    </Card>
  );
}

export function SettingsPage() {
  return (
    <div className="flex flex-col gap-3 p-4 max-w-lg mx-auto">
      <h1 className="text-lg font-semibold">Settings</h1>
      <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mt-2">Organisation</h2>
      <SettingList
        settingKey="recipients"
        label="Recipients"
        description="People or entities who receive letters at this address. The LLM uses this list to assign each letter to the right recipient."
      />
      <SettingList
        settingKey="tags"
        label="Tags"
        description="A vocabulary of labels the LLM can assign to letters (e.g. 'invoice', 'tax', 'insurance'). Add tags here to help the LLM categorise your mail."
      />
      <SettingList
        settingKey="translation_languages"
        label="Translation Languages"
        description="Languages available for on-demand letter translation. Click a language on any letter to generate a translation."
      />
      <h2 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mt-2">Technical</h2>
      <OpenRouterCredits />
      <DateFormatToggle />
      <DewarpingMethodToggle />
    </div>
  );
}
