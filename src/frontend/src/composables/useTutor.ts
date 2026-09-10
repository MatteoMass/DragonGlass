/**
 * The exam tutor: staging an import, mapping its columns, and taking a quiz.
 *
 * One instance is shared by the whole app, the same way `useHollow` is: the
 * tutor view reads and drives everything through here rather than holding
 * its own copies.
 */

import { ref } from 'vue'

import { ApiError } from '@/api/http'
import {
  tutorApi,
  type TutorCommitPayload,
  type TutorImport,
  type TutorMode,
  type TutorQuiz,
  type TutorQuizSummary,
} from '@/api/tutor'

const quizzes = ref<TutorQuizSummary[]>([])
const pendingImport = ref<TutorImport | null>(null)
const activeQuiz = ref<TutorQuiz | null>(null)
const loading = ref(false)
const error = ref('')

/** The shared tutor state, and the operations that change it. */
export function useTutor() {
  /** Run an operation, reporting whatever the backend refused it with. */
  async function attempt<T>(operation: () => Promise<T>): Promise<T | null> {
    error.value = ''
    try {
      return await operation()
    } catch (raised) {
      error.value = raised instanceof ApiError ? raised.message : 'Unexpected error'
      return null
    }
  }

  /** Reload the list of quiz sets from the server. */
  async function loadQuizzes(): Promise<void> {
    loading.value = true
    const fetched = await attempt(() => tutorApi.listTutorQuizzes())
    if (fetched) quizzes.value = fetched
    loading.value = false
  }

  /** Upload a .csv or .xlsx and stage it for column mapping. */
  async function stageImport(file: File): Promise<boolean> {
    const staged = await attempt(() => tutorApi.stageTutorImport(file))
    if (!staged) return false
    pendingImport.value = staged
    return true
  }

  /** Abandon a staged import without building a quiz out of it. */
  function cancelImport(): void {
    pendingImport.value = null
  }

  /** Map the staged import's columns and build a quiz set out of it, images included. */
  async function commitImport(payload: TutorCommitPayload, images: File[] = []): Promise<boolean> {
    const staged = pendingImport.value
    if (!staged) return false
    const quiz = await attempt(() => tutorApi.commitTutorImport(staged.importId, payload, images))
    if (!quiz) return false
    pendingImport.value = null
    activeQuiz.value = quiz
    await loadQuizzes()
    return true
  }

  /** Open a persisted quiz set to take it. */
  async function openQuiz(id: string): Promise<void> {
    const quiz = await attempt(() => tutorApi.getTutorQuiz(id))
    if (quiz) activeQuiz.value = quiz
  }

  /** Close the open quiz set, back to the list. */
  function closeQuiz(): void {
    activeQuiz.value = null
  }

  /** Give the open quiz set a new name. */
  async function renameQuiz(id: string, name: string): Promise<boolean> {
    const quiz = await attempt(() => tutorApi.renameTutorQuiz(id, name))
    if (!quiz) return false
    activeQuiz.value = quiz
    await loadQuizzes()
    return true
  }

  /** Re-resolve the open quiz set's references within one folder, subfolders included. */
  async function setReferenceFolder(id: string, folder: string): Promise<boolean> {
    const quiz = await attempt(() => tutorApi.setTutorReferenceFolder(id, folder))
    if (!quiz) return false
    activeQuiz.value = quiz
    return true
  }

  /** Record how one completed run through the open quiz set went. */
  async function recordAttempt(
    id: string,
    mode: TutorMode,
    questionCount: number,
    correctCount: number,
  ): Promise<boolean> {
    const quiz = await attempt(() => tutorApi.recordTutorAttempt(id, mode, questionCount, correctCount))
    if (!quiz) return false
    activeQuiz.value = quiz
    return true
  }

  /** Add a note to a question of the open quiz set, after it has been answered. */
  async function addNote(questionId: string, text: string): Promise<boolean> {
    const quiz = activeQuiz.value
    if (!quiz) return false
    const updated = await attempt(() => tutorApi.addTutorNote(quiz.id, questionId, text))
    if (!updated) return false
    activeQuiz.value = updated
    return true
  }

  /** Change one note's text, independently of its question's other notes. */
  async function updateNote(questionId: string, noteId: string, text: string): Promise<boolean> {
    const quiz = activeQuiz.value
    if (!quiz) return false
    const updated = await attempt(() => tutorApi.updateTutorNote(quiz.id, questionId, noteId, text))
    if (!updated) return false
    activeQuiz.value = updated
    return true
  }

  /** Delete one note, independently of its question's other notes. */
  async function deleteNote(questionId: string, noteId: string): Promise<boolean> {
    const quiz = activeQuiz.value
    if (!quiz) return false
    const updated = await attempt(() => tutorApi.deleteTutorNote(quiz.id, questionId, noteId))
    if (!updated) return false
    activeQuiz.value = updated
    return true
  }

  /** Delete a quiz set. */
  async function deleteQuiz(id: string): Promise<void> {
    const done = await attempt(async () => {
      await tutorApi.deleteTutorQuiz(id)
      return true
    })
    if (!done) return
    if (activeQuiz.value?.id === id) activeQuiz.value = null
    await loadQuizzes()
  }

  /** Clear the last reported error. */
  function clearError(): void {
    error.value = ''
  }

  return {
    quizzes,
    pendingImport,
    activeQuiz,
    loading,
    error,
    loadQuizzes,
    stageImport,
    cancelImport,
    commitImport,
    openQuiz,
    closeQuiz,
    renameQuiz,
    setReferenceFolder,
    recordAttempt,
    addNote,
    updateNote,
    deleteNote,
    deleteQuiz,
    clearError,
  }
}
