import { SavedLibraryView } from "@/components/SavedLibraryView";
import { parseSavedLibraryState } from "@/lib/savedLibrary";

export default async function LibraryPage({
  searchParams,
}: Readonly<{
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}>) {
  const initialState = parseSavedLibraryState(await searchParams);

  return <SavedLibraryView initialState={initialState} />;
}
