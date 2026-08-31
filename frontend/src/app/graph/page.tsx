import { GraphView } from "@/components/GraphView";
import { parseGraphSearchState } from "@/lib/globalSearch";
import { parseLearningWorkflowContext } from "@/lib/learningWorkflow";

export default async function GraphPage({
  searchParams,
}: Readonly<{
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}>) {
  const query = await searchParams;
  const initialContext = parseLearningWorkflowContext(query);
  const initialSearch = parseGraphSearchState(query);

  return <GraphView initialContext={initialContext} initialSearch={initialSearch} />;
}
