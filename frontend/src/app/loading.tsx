import { WorkspaceState } from "@/components/WorkspaceState";

export default function Loading() {
  return (
    <WorkspaceState
      detail="Preparing the current view."
      testId="route-loading-state"
      title="Loading workspace"
      tone="loading"
    />
  );
}
