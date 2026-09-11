/** The tutor plugin's own types and HTTP calls: importing a spreadsheet and taking it as a quiz. */

import { json, request } from './http'

/** A spreadsheet staged for column mapping, before it becomes a quiz. */
export interface TutorImport {
  /** The id this staged import is held under; the mapping step commits against it. */
  importId: string
  /** The name the upload arrived with. */
  filename: string
  /** The header row. */
  columns: string[]
  /** The first few data rows, shown while columns are picked. */
  previewRows: string[][]
}

/** The body that turns a staged import into a quiz set. */
export interface TutorCommitPayload {
  /** The name to give the quiz set. */
  name: string
  /** The column holding each question's text. */
  questionColumn: string
  /** The columns holding each answer, in display order. */
  answerColumns: string[]
  /** The column naming the correct answer of each row. */
  correctColumn: string
  /** The column holding a reference note's name, if any. */
  referenceColumn: string | null
  /** Whether the reference column may name more than one source, joined by `referenceSeparator`. */
  multiReference: boolean
  /** The literal that splits a reference label into several source names, used only when
   *  `multiReference` is set. */
  referenceSeparator: string
  /** Whether uploaded images should be matched to the rows that name them. */
  includeImages: boolean
  /** The columns to search for an uploaded image's name, used only when `includeImages`
   *  is set. Usually the question column, but answer columns may be included too. */
  imageColumns: string[]
}

/** One note left on a question, after it was answered. */
export interface TutorNote {
  /** The note's id, stable within its question. */
  id: string
  /** The note's text. */
  text: string
  /** When it was written, ISO 8601. */
  createdAt: string
}

/** One question of a quiz set. */
export interface TutorQuestion {
  /** The question's id, stable within its quiz set. */
  id: string
  /** The question text. */
  question: string
  /** The possible answers, in the order they show. */
  answers: string[]
  /** The indices into `answers` that are correct -- more than one for a multi-answer question. */
  correctIndices: number[]
  /** The reference label, empty when the row had none. */
  reference: string
  /** The hollow-relative paths each source in `reference` resolved to; a source that
   *  matched nothing is left out. */
  referencePaths: string[]
  /** The notes left on this question, oldest first. */
  notes: TutorNote[]
  /** The tutor-relative paths of the images matched to this question at import time. */
  imagePaths: string[]
}

/** How a quiz's questions are chosen for one attempt. */
export type TutorMode = 'sequential' | 'random' | 'manual'

/** One completed run through a quiz set, kept for its statistics. */
export interface TutorAttempt {
  /** The attempt's id. */
  id: string
  /** How its questions were chosen. */
  mode: TutorMode
  /** How many questions the attempt covered. */
  questionCount: number
  /** How many of them were answered correctly. */
  correctCount: number
  /** When the attempt was recorded, ISO 8601. */
  completedAt: string
}

/** A quiz set, questions included. */
export interface TutorQuiz {
  /** The quiz set's id. */
  id: string
  /** The name it was given at import time. */
  name: string
  /** When it was built, ISO 8601. */
  createdAt: string
  /** Its questions, in source order. */
  questions: TutorQuestion[]
  /** Every completed run through it, oldest first. */
  attempts: TutorAttempt[]
  /** The hollow-relative folder its references were last resolved against, subfolders
   *  included; empty means the whole hollow. */
  referenceFolder: string
  /** The literal that splits a reference label into several source names, empty when
   *  each label names a single source. */
  referenceSeparator: string
}

/** A quiz set without its questions, for a list view. */
export interface TutorQuizSummary {
  /** The quiz set's id. */
  id: string
  /** The name it was given at import time. */
  name: string
  /** When it was built, ISO 8601. */
  createdAt: string
  /** How many questions it holds. */
  questionCount: number
}

export const tutorApi = {
  /** Stage a .csv or .xlsx spreadsheet, parsed and ready for column mapping. */
  stageTutorImport(file: File): Promise<TutorImport> {
    const form = new FormData()
    form.append('file', file)
    return request<TutorImport>('/tutor/imports', { method: 'POST', body: form })
  },

  /** Map columns of a staged import and build a persisted quiz set out of it, images
   *  it should be matched against rows included. */
  commitTutorImport(
    importId: string,
    payload: TutorCommitPayload,
    images: File[] = [],
  ): Promise<TutorQuiz> {
    const form = new FormData()
    form.append('payload', JSON.stringify(payload))
    for (const image of images) form.append('images', image)
    return request<TutorQuiz>(`/tutor/imports/${encodeURIComponent(importId)}/commit`, {
      method: 'POST',
      body: form,
    })
  },

  /** Every persisted quiz set, without its questions. */
  listTutorQuizzes(): Promise<TutorQuizSummary[]> {
    return request<TutorQuizSummary[]>('/tutor/quizzes')
  },

  /** One persisted quiz set, questions included. */
  getTutorQuiz(id: string): Promise<TutorQuiz> {
    return request<TutorQuiz>(`/tutor/quizzes/${encodeURIComponent(id)}`)
  },

  /** Give a quiz set a new name. */
  renameTutorQuiz(id: string, name: string): Promise<TutorQuiz> {
    return request<TutorQuiz>(`/tutor/quizzes/${encodeURIComponent(id)}`, json('PATCH', { name }))
  },

  /** Re-resolve a quiz set's references within one folder of the hollow, subfolders included. */
  setTutorReferenceFolder(id: string, folder: string): Promise<TutorQuiz> {
    return request<TutorQuiz>(
      `/tutor/quizzes/${encodeURIComponent(id)}/reference-folder`,
      json('PATCH', { folder }),
    )
  },

  /** Record how one completed run through a quiz set went, for its statistics. */
  recordTutorAttempt(
    id: string,
    mode: TutorMode,
    questionCount: number,
    correctCount: number,
  ): Promise<TutorQuiz> {
    return request<TutorQuiz>(
      `/tutor/quizzes/${encodeURIComponent(id)}/attempts`,
      json('POST', { mode, questionCount, correctCount }),
    )
  },

  /** Delete a quiz set. */
  deleteTutorQuiz(id: string): Promise<void> {
    return request<void>(`/tutor/quizzes/${encodeURIComponent(id)}`, { method: 'DELETE' })
  },

  /** Add a note to a question, after it has been answered. */
  addTutorNote(quizId: string, questionId: string, text: string): Promise<TutorQuiz> {
    return request<TutorQuiz>(
      `/tutor/quizzes/${encodeURIComponent(quizId)}/questions/${encodeURIComponent(questionId)}/notes`,
      json('POST', { text }),
    )
  },

  /** Change one note's text, independently of the question's other notes. */
  updateTutorNote(
    quizId: string,
    questionId: string,
    noteId: string,
    text: string,
  ): Promise<TutorQuiz> {
    return request<TutorQuiz>(
      `/tutor/quizzes/${encodeURIComponent(quizId)}/questions/${encodeURIComponent(questionId)}` +
        `/notes/${encodeURIComponent(noteId)}`,
      json('PATCH', { text }),
    )
  },

  /** Delete one note, independently of the question's other notes. */
  deleteTutorNote(quizId: string, questionId: string, noteId: string): Promise<TutorQuiz> {
    return request<TutorQuiz>(
      `/tutor/quizzes/${encodeURIComponent(quizId)}/questions/${encodeURIComponent(questionId)}` +
        `/notes/${encodeURIComponent(noteId)}`,
      { method: 'DELETE' },
    )
  },
}
