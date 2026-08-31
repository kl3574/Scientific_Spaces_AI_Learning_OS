import { ArticleDetailView } from "@/components/ArticleDetailView";
import { sanitizeArticleListReturnPath } from "@/lib/learningWorkflow";

export default async function ArticlePage({
  params,
  searchParams,
}: Readonly<{
  params: Promise<{ id: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}>) {
  const [{ id }, query] = await Promise.all([params, searchParams]);
  const rawReturnTo = Array.isArray(query.from) ? query.from[0] : query.from;
  const listReturnTo = sanitizeArticleListReturnPath(rawReturnTo);

  return <ArticleDetailView articleId={id} listReturnTo={listReturnTo} />;
}
