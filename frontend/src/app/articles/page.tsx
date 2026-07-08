import { ArticleListView } from "@/components/ArticleListView";
import { ReaderShell } from "@/components/ReaderShell";

export default function ArticlesPage() {
  return (
    <ReaderShell>
      <ArticleListView />
    </ReaderShell>
  );
}
