import { NavLink } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { fetchTasks } from "@/api/client";

const navItems = [
  { to: "/", label: "Ingest", icon: "+" },
  { to: "/archive", label: "Archive", icon: "📋" },
  { to: "/tasks", label: "Tasks", icon: "✓" },
  { to: "/settings", label: "Settings", icon: "⚙" },
];

interface SideNavProps {
  collapsed: boolean;
  onToggle: () => void;
}

export function SideNav({ collapsed, onToggle }: SideNavProps) {
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
    <aside
      className={`hidden md:flex fixed left-0 top-0 h-full flex-col bg-card shadow-sm z-50 transition-all duration-200 ${
        collapsed ? "w-12" : "w-44"
      }`}
    >
      {/* Header */}
      <div className={`flex items-center border-b h-14 shrink-0 ${collapsed ? "justify-center" : "px-4 gap-2"}`}>
        {!collapsed && (
          <span className="text-sm font-semibold text-primary tracking-wide flex-1 truncate">
            Letter Scanner
          </span>
        )}
        <button
          onClick={onToggle}
          className="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground transition-colors shrink-0"
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? "›" : "‹"}
        </button>
      </div>

      {/* Nav items */}
      <nav className="flex flex-col gap-1 p-2 flex-1">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            title={collapsed ? item.label : undefined}
            className={({ isActive }) =>
              `flex items-center rounded-lg text-sm transition-colors ${
                collapsed ? "justify-center px-0 py-2" : "gap-3 px-3 py-2"
              } ${
                isActive
                  ? "bg-accent text-accent-foreground font-medium"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              }`
            }
          >
            <span className="relative text-base leading-none shrink-0">
              {item.icon}
              {item.label === "Tasks" && overdueCount > 0 && (
                <span className="absolute -right-2 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-destructive text-[10px] text-white">
                  {overdueCount}
                </span>
              )}
            </span>
            {!collapsed && <span>{item.label}</span>}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
