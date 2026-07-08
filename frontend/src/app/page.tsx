import { DashboardView } from "@/components/DashboardView";
import { ReaderShell } from "@/components/ReaderShell";

export default function Home() {
  return (
    <ReaderShell>
      <DashboardView />
    </ReaderShell>
  );
}
