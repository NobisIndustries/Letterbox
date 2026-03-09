import { NavLink } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { fetchTasks } from "@/api/client";

const navItems = [
  { to: "/", label: "Ingest", icon: "+" },
  { to: "/archive", label: "Archive", icon: "📋" },
  { to: "/tasks", label: "Tasks", icon: "✓" },
  { to: "/settings", label: "Settings", icon: "⚙" },
];

export function BottomNav() {
  const { data: tasks } = useQuery({
    queryKey: ["tasks", "pending"],
    queryFn: () => fetchTasks("pending"),
    refetchInterval: 30000,
  });

  const overdueCount =
    tasks?.filter(
      (t) => t.deadline && new Date(t.deadline) < new Date() && !t.is_done
    ).length ?? 0;

  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 z-50 border-t bg-background">
      <div className="flex justify-around">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `flex flex-1 flex-col items-center gap-0.5 py-2 text-xs transition-colors ${
                isActive
                  ? "text-primary font-semibold"
                  : "text-muted-foreground"
              }`
            }
          >
            <span className="relative text-lg">
              {item.icon}
              {item.label === "Tasks" && overdueCount > 0 && (
                <span className="absolute -right-2 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-destructive text-[10px] text-white">
                  {overdueCount}
                </span>
              )}
            </span>
            <span>{item.label}</span>
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
