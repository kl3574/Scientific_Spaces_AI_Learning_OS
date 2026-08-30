import type {
  ArticleOutlineItem,
  ReaderPreferences,
  ReaderTextSize,
  ReaderWidth,
} from "@/lib/articleWorkspace";

export function ReadingProgress({
  activeSection,
  progress,
}: Readonly<{ activeSection: ArticleOutlineItem | null; progress: number }>) {
  return (
    <>
      <div aria-hidden="true" className="fixed inset-x-0 top-0 z-[70] h-1 bg-slate-200">
        <div
          className="h-full bg-emerald-700 motion-safe:transition-[width] motion-safe:duration-150"
          style={{ width: `${progress}%` }}
        />
      </div>
      <div
        aria-label="Reading progress"
        aria-valuemax={100}
        aria-valuemin={0}
        aria-valuenow={progress}
        className="mt-4 flex min-w-0 items-center justify-between gap-3 border-y border-slate-200 py-2 text-xs text-slate-600"
        data-testid="reading-progress"
        role="progressbar"
      >
        <span className="min-w-0 truncate">{activeSection?.label ?? "Article start"}</span>
        <span className="shrink-0 font-semibold tabular-nums text-slate-800">{progress}% read</span>
      </div>
    </>
  );
}

export function ArticleOutline({
  activeSectionId,
  items,
  onNavigate,
}: Readonly<{
  activeSectionId: string | null;
  items: ArticleOutlineItem[];
  onNavigate: (sectionId: string) => void;
}>) {
  return (
    <nav aria-label="Article outline" data-testid="article-outline">
      <h2 className="text-base font-semibold">On this page</h2>
      {items.length ? (
        <ol className="mt-3 space-y-1 border-l border-slate-200 pl-3 text-sm">
          {items.map((item) => (
            <li key={item.id} className={item.level >= 3 ? "pl-3" : undefined}>
              <a
                aria-current={activeSectionId === item.id ? "location" : undefined}
                className={
                  activeSectionId === item.id
                    ? "block border-l-2 border-emerald-700 py-1 pl-2 font-semibold text-emerald-900"
                    : "block border-l-2 border-transparent py-1 pl-2 text-slate-600 hover:text-slate-950"
                }
                href={`#${encodeURIComponent(item.id)}`}
                onClick={(event) => {
                  event.preventDefault();
                  onNavigate(item.id);
                }}
              >
                {item.label}
              </a>
            </li>
          ))}
        </ol>
      ) : (
        <p className="mt-3 text-sm text-slate-500">No sections detected.</p>
      )}
    </nav>
  );
}

export function ReaderDisplayControls({
  preferences,
  onChange,
}: Readonly<{
  preferences: ReaderPreferences;
  onChange: (preferences: ReaderPreferences) => void;
}>) {
  const textSizes: Array<{ value: ReaderTextSize; label: string; visual: string }> = [
    { value: "compact", label: "Compact text", visual: "A-" },
    { value: "comfortable", label: "Comfortable text", visual: "A" },
    { value: "large", label: "Large text", visual: "A+" },
  ];
  const widths: Array<{ value: ReaderWidth; label: string }> = [
    { value: "focused", label: "Focus" },
    { value: "wide", label: "Wide" },
  ];

  return (
    <section aria-labelledby="reader-display-heading">
      <h2 id="reader-display-heading" className="text-base font-semibold">Display</h2>
      <fieldset className="mt-3">
        <legend className="text-xs font-medium text-slate-500">Text size</legend>
        <div className="mt-2 grid grid-cols-3 overflow-hidden rounded border border-slate-300" role="group">
          {textSizes.map((option) => (
            <button
              key={option.value}
              aria-label={option.label}
              aria-pressed={preferences.textSize === option.value}
              className={
                preferences.textSize === option.value
                  ? "h-9 border-r border-slate-300 bg-slate-950 px-2 text-sm font-semibold text-white last:border-r-0"
                  : "h-9 border-r border-slate-300 bg-white px-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 last:border-r-0"
              }
              type="button"
              onClick={() => onChange({ ...preferences, textSize: option.value })}
            >
              {option.visual}
            </button>
          ))}
        </div>
      </fieldset>
      <fieldset className="mt-3">
        <legend className="text-xs font-medium text-slate-500">Reading width</legend>
        <div className="mt-2 grid grid-cols-2 overflow-hidden rounded border border-slate-300" role="group">
          {widths.map((option) => (
            <button
              key={option.value}
              aria-pressed={preferences.width === option.value}
              className={
                preferences.width === option.value
                  ? "h-9 border-r border-slate-300 bg-slate-950 px-2 text-xs font-semibold text-white last:border-r-0"
                  : "h-9 border-r border-slate-300 bg-white px-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 last:border-r-0"
              }
              type="button"
              onClick={() => onChange({ ...preferences, width: option.value })}
            >
              {option.label}
            </button>
          ))}
        </div>
      </fieldset>
    </section>
  );
}
