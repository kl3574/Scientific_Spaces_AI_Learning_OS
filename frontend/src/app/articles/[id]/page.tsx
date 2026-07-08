import { ArticleDetailView } from "@/components/ArticleDetailView";
import { ReaderShell } from "@/components/ReaderShell";

export default async function ArticlePage({ params }: Readonly<{ params: Promise<{ id: string }> }>) {
  const { id } = await params;

  return (
    <ReaderShell>
      <ArticleDetailView articleId={id} />
    </ReaderShell>
  );
}
