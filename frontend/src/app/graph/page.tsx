import { GraphView } from "@/components/GraphView";
import { parseLearningWorkflowContext } from "@/lib/learningWorkflow";

export default async function GraphPage({
  searchParams,
}: Readonly<{
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}>) {
  const initialContext = parseLearningWorkflowContext(await searchParams);

  return <GraphView initialContext={initialContext} />;
}
