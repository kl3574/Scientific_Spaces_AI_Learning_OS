import { ArticleListView } from "@/components/ArticleListView";
import { ReaderShell } from "@/components/ReaderShell";
import { parseArticleListState } from "@/lib/learningWorkflow";

export default async function ArticlesPage({
  searchParams,
}: Readonly<{
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}>) {
  const initialState = parseArticleListState(await searchParams);

  return (
    <ReaderShell>
      <ArticleListView initialState={initialState} />
    </ReaderShell>
  );
}
