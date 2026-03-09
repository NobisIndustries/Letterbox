import { Route, Routes } from "react-router-dom";
import { BottomNav } from "@/components/BottomNav";
import { IngestPage } from "@/pages/IngestPage";
import { ArchivePage } from "@/pages/ArchivePage";
import { LetterDetailPage } from "@/pages/LetterDetailPage";
import { TasksPage } from "@/pages/TasksPage";
import { SettingsPage } from "@/pages/SettingsPage";

function App() {
  return (
    <div className="min-h-screen pb-16">
      <Routes>
        <Route path="/" element={<IngestPage />} />
        <Route path="/archive" element={<ArchivePage />} />
        <Route path="/letters/:id" element={<LetterDetailPage />} />
        <Route path="/tasks" element={<TasksPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
      <BottomNav />
    </div>
  );
}

export default App;
