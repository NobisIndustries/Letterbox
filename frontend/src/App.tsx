import { useState } from "react";
import { Route, Routes } from "react-router-dom";
import { BottomNav } from "@/components/BottomNav";
import { SideNav } from "@/components/SideNav";
import { JobStatusBar } from "@/components/JobStatusBar";
import { IngestPage } from "@/pages/IngestPage";
import { ArchivePage } from "@/pages/ArchivePage";
import { LetterDetailPage } from "@/pages/LetterDetailPage";
import { TasksPage } from "@/pages/TasksPage";
import { SettingsPage } from "@/pages/SettingsPage";

function App() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [jobIds, setJobIds] = useState<string[]>([]);

  const addJobId = (id: string) => setJobIds((prev) => [...prev, id]);
  const dismissJob = (id: string) => setJobIds((prev) => prev.filter((j) => j !== id));

  return (
    <div className="min-h-screen">
      <SideNav collapsed={sidebarCollapsed} onToggle={() => setSidebarCollapsed((c) => !c)} />
      <div className={`transition-all duration-200 pb-16 md:pb-0 ${sidebarCollapsed ? "md:ml-12" : "md:ml-44"}`}>
        <Routes>
          <Route path="/" element={<IngestPage onJobCreated={addJobId} />} />
          <Route path="/archive" element={<ArchivePage />} />
          <Route path="/letters/:id" element={<LetterDetailPage />} />
          <Route path="/tasks" element={<TasksPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </div>
      <JobStatusBar jobIds={jobIds} onDismiss={dismissJob} onForceJob={addJobId} />
      <BottomNav />
    </div>
  );
}

export default App;
