import { ReaderShell } from "@/components/ReaderShell";
import { TutorView } from "@/components/TutorView";
import { parseLearningWorkflowContext } from "@/lib/learningWorkflow";

export default async function TutorPage({
  searchParams,
}: Readonly<{
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}>) {
  const initialContext = parseLearningWorkflowContext(await searchParams);

  return (
    <ReaderShell>
      <TutorView initialContext={initialContext} />
    </ReaderShell>
  );
}
