import { ArticleDetailView } from "@/components/ArticleDetailView";
import { sanitizeArticleEntryReturnPath } from "@/lib/learningWorkflow";

export default async function ArticlePage({
  params,
  searchParams,
}: Readonly<{
  params: Promise<{ id: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}>) {
  const [{ id }, query] = await Promise.all([params, searchParams]);
  const rawReturnTo = Array.isArray(query.from) ? query.from[0] : query.from;
  const listReturnTo = sanitizeArticleEntryReturnPath(rawReturnTo);

  return <ArticleDetailView articleId={id} listReturnTo={listReturnTo} />;
}
