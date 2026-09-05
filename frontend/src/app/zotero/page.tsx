import { ZoteroLibraryView } from "@/components/ZoteroLibraryView";
import {
  createReferenceReviewHref,
  isCanonicalReferenceReviewSearchParams,
  parseReferenceReviewState,
} from "@/lib/referenceReview";
import { redirect } from "next/navigation";

export default async function ZoteroPage({
  searchParams,
}: Readonly<{
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}>) {
  const rawSearchParams = await searchParams;
  const initialReferenceState = parseReferenceReviewState(rawSearchParams);
  if (!isCanonicalReferenceReviewSearchParams(rawSearchParams, initialReferenceState)) {
    redirect(createReferenceReviewHref(initialReferenceState));
  }

  return <ZoteroLibraryView initialReferenceState={initialReferenceState} />;
}
