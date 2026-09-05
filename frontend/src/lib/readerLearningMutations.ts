import type { LearningNote } from "./learning";

export type ReaderMutationKind =
  | "bookmark-add"
  | "bookmark-remove"
  | "note-create"
  | "note-update"
  | "note-delete";

export type ReaderMutationOperation = Readonly<{
  articleId: string;
  generation: number;
  operationId: number;
  kind: ReaderMutationKind;
  noteId: string | null;
}>;

export function createReaderMutationOperation(
  articleId: string,
  generation: number,
  operationId: number,
  kind: ReaderMutationKind,
  noteId: string | null = null,
): ReaderMutationOperation {
  return { articleId, generation, operationId, kind, noteId };
}

export function ownsReaderMutation(
  current: ReaderMutationOperation | null,
  operation: ReaderMutationOperation,
  articleId: string,
  generation: number,
): boolean {
  return current !== null
    && current.articleId === operation.articleId
    && current.generation === operation.generation
    && current.operationId === operation.operationId
    && current.kind === operation.kind
    && current.noteId === operation.noteId
    && articleId === operation.articleId
    && generation === operation.generation;
}

export function mergeCreatedLearningNote(
  notes: LearningNote[],
  incoming: LearningNote,
  articleId: string,
): LearningNote[] {
  if (incoming.article_id !== articleId) {
    return notes;
  }
  return [incoming, ...notes.filter((note) => note.note_id !== incoming.note_id)];
}

export function mergeUpdatedLearningNote(
  notes: LearningNote[],
  incoming: LearningNote,
  articleId: string,
): LearningNote[] {
  if (incoming.article_id !== articleId) {
    return notes;
  }
  const existingIndex = notes.findIndex((note) => note.note_id === incoming.note_id);
  if (existingIndex < 0) {
    return notes;
  }
  return notes
    .filter((note, index) => note.note_id !== incoming.note_id || index === existingIndex)
    .map((note, index) => (index === existingIndex ? incoming : note));
}

export function removeLearningNote(notes: LearningNote[], noteId: string): LearningNote[] {
  if (!notes.some((note) => note.note_id === noteId)) {
    return notes;
  }
  return notes.filter((note) => note.note_id !== noteId);
}
