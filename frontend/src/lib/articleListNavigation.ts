import { createArticleListHref, parseArticleListState } from "./learningWorkflow";

type ArticleListRouteSnapshot = Readonly<{
  pathname: string;
  search: string;
  browserPathname: string;
  browserSearch: string;
  knownHref: string;
}>;

export function getArticleListRoutePlan(snapshot: ArticleListRouteSnapshot) {
  if (
    snapshot.pathname !== "/articles"
    || snapshot.browserPathname !== snapshot.pathname
    || new URLSearchParams(snapshot.search).toString()
      !== new URLSearchParams(snapshot.browserSearch).toString()
  ) {
    return null;
  }

  const state = parseArticleListState(new URLSearchParams(snapshot.search));
  const href = createArticleListHref(state);
  return {
    action: href === snapshot.knownHref ? "echo" as const : "navigate" as const,
    state,
    href,
  };
}
