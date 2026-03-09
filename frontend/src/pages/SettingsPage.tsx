import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { fetchSetting, updateSetting } from "@/api/client";

function SettingList({ settingKey, label }: { settingKey: string; label: string }) {
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

export function SettingsPage() {
  return (
    <div className="flex flex-col gap-3 p-4 max-w-lg mx-auto">
      <h1 className="text-lg font-semibold">Settings</h1>
      <SettingList settingKey="recipients" label="Recipients" />
      <SettingList settingKey="tags" label="Tags" />
    </div>
  );
}
