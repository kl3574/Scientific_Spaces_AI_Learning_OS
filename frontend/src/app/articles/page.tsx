import { ArticleListView } from "@/components/ArticleListView";
import { parseArticleListState } from "@/lib/learningWorkflow";

export default async function ArticlesPage({
  searchParams,
}: Readonly<{
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}>) {
  const initialState = parseArticleListState(await searchParams);

  return <ArticleListView initialState={initialState} />;
}
