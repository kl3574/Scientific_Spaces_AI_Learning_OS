import { TutorView } from "@/components/TutorView";
import { parseConceptTutorLaunch } from "@/lib/conceptLearningLaunch";
import { parseLearningWorkflowContext } from "@/lib/learningWorkflow";

export default async function TutorPage({
  searchParams,
}: Readonly<{
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}>) {
  const query = await searchParams;
  const initialConcept = parseConceptTutorLaunch(query);
  const initialContext = initialConcept ? null : parseLearningWorkflowContext(query);

  return <TutorView initialConcept={initialConcept} initialContext={initialContext} />;
}
