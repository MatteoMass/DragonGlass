<script setup lang="ts">
/**
 * The exam tutor plugin: import a spreadsheet, map its columns, configure and take a quiz.
 *
 * Four stages, switched on what `useTutor` currently holds and on the local
 * `takingSession` flag: the list of quiz sets (with the import button), the
 * column-mapping form for a staged import, a quiz set's detail page (its
 * name, its statistics, and the mode an attempt is configured with), and
 * taking the configured attempt one question at a time. A reference opens
 * beside the question rather than replacing it, so the answer stays in view
 * while the source it came from is read.
 */
import { computed, ref, watch } from 'vue'

import { ApiError, api, type Note, type TreeNode } from '@/api/client'
import type { TutorMode, TutorNote, TutorQuestion } from '@/api/tutor'
import { useAppView } from '@/composables/useAppView'
import { useConfirm } from '@/composables/useConfirm'
import { useHollow } from '@/composables/useHollow'
import { usePrompt } from '@/composables/usePrompt'
import { useTutor } from '@/composables/useTutor'

const tutor = useTutor()
const hollow = useHollow()
const { view } = useAppView()
const { ask } = useConfirm()
const { ask: askName } = usePrompt()

const fileInput = ref<HTMLInputElement | null>(null)

/* ---------------------------------------------------------- import & mapping -- */

const name = ref('')
const questionColumn = ref('')
const answerColumns = ref<string[]>([])
const correctColumn = ref('')
const referenceColumn = ref('')
const multiReference = ref(false)
const referenceSeparator = ref(';')
const includeImages = ref(false)
const imageColumn = ref('')
const imageFiles = ref<File[]>([])
const mappingError = ref('')

watch(
  () => tutor.pendingImport.value,
  (staged) => {
    if (!staged) return
    name.value = staged.filename.replace(/\.(csv|xlsx)$/i, '')
    questionColumn.value = staged.columns[0] ?? ''
    answerColumns.value = []
    correctColumn.value = ''
    referenceColumn.value = ''
    multiReference.value = false
    referenceSeparator.value = ';'
    includeImages.value = false
    imageColumn.value = ''
    imageFiles.value = []
    mappingError.value = ''
  },
)

/** Default the image column to the question column, the first time images are turned on. */
watch(includeImages, (on) => {
  if (on && !imageColumn.value) imageColumn.value = questionColumn.value
})

/** Keep the chosen image files in sync with the file input. */
function onImagesChosen(event: Event): void {
  const input = event.target as HTMLInputElement
  imageFiles.value = input.files ? Array.from(input.files) : []
}

/** Send the chosen file off to be staged, whatever format it is. */
async function onFileChosen(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (file) await tutor.stageImport(file)
}

/** Build the quiz set once the mapping looks usable. */
async function submitMapping(): Promise<void> {
  mappingError.value = ''
  if (!questionColumn.value || !correctColumn.value) {
    mappingError.value = 'Pick a question column and a correct-answer column.'
    return
  }
  if (answerColumns.value.length < 2) {
    mappingError.value = 'Pick at least two answer columns.'
    return
  }
  if (multiReference.value && !referenceSeparator.value) {
    mappingError.value = 'Give the separator between references.'
    return
  }
  if (includeImages.value && !imageColumn.value) {
    mappingError.value = 'Pick which column names each image.'
    return
  }
  if (includeImages.value && imageFiles.value.length === 0) {
    mappingError.value = 'Choose the images to match against that column.'
    return
  }
  await tutor.commitImport(
    {
      name: name.value,
      questionColumn: questionColumn.value,
      answerColumns: answerColumns.value,
      correctColumn: correctColumn.value,
      referenceColumn: referenceColumn.value || null,
      multiReference: multiReference.value,
      referenceSeparator: referenceSeparator.value,
      includeImages: includeImages.value,
      imageColumn: includeImages.value ? imageColumn.value : null,
    },
    includeImages.value ? imageFiles.value : [],
  )
}

/** Delete a quiz set, once the user confirms. */
async function removeQuiz(id: string, label: string): Promise<void> {
  const agreed = await ask('Delete the quiz', `"${label}" will be removed. This cannot be undone.`, {
    confirmLabel: 'Delete',
    danger: true,
  })
  if (agreed) await tutor.deleteQuiz(id)
}

/* -------------------------------------------------------------------- detail -- */

const takingSession = ref(false)
const mode = ref<TutorMode>('sequential')
const limit = ref(1)
const manualSelection = ref<Set<string>>(new Set())
const startError = ref('')

const quiz = computed(() => tutor.activeQuiz.value)
const totalQuestions = computed(() => quiz.value?.questions.length ?? 0)
const attempts = computed(() => quiz.value?.attempts ?? [])
const attemptCount = computed(() => attempts.value.length)
const bestScore = computed(() => {
  if (!attempts.value.length) return null
  return Math.max(...attempts.value.map((a) => a.correctCount / a.questionCount))
})
const lastAttempt = computed(() => attempts.value[attempts.value.length - 1] ?? null)

/** A ratio as a rounded percentage. */
function pct(ratio: number): string {
  return `${Math.round(ratio * 100)}%`
}

const referenceFolder = ref('')
const referenceCount = computed(
  () => quiz.value?.questions.filter((q) => q.reference).length ?? 0,
)
const resolvedReferenceCount = computed(
  () => quiz.value?.questions.filter((q) => q.referencePaths.length > 0).length ?? 0,
)

/** Every folder of the hollow, indented by depth, for the reference-folder picker. */
const folderOptions = computed(() => {
  const options: { path: string; label: string }[] = []
  function walk(nodes: TreeNode[], depth: number): void {
    for (const node of nodes) {
      if (node.kind !== 'folder') continue
      options.push({ path: node.path, label: `${'  '.repeat(depth)}${node.name}` })
      if (node.children) walk(node.children, depth + 1)
    }
  }
  walk(hollow.tree.value, 0)
  return options
})

/** Re-resolve the quiz's references against the chosen folder. */
async function applyReferenceFolder(): Promise<void> {
  if (!quiz.value) return
  await tutor.setReferenceFolder(quiz.value.id, referenceFolder.value)
}

/** A fresh detail configuration whenever a *different* quiz set is opened. */
watch(
  () => quiz.value?.id,
  (id, previousId) => {
    if (!id || id === previousId) return
    takingSession.value = false
    mode.value = 'sequential'
    limit.value = quiz.value?.questions.length ?? 1
    manualSelection.value = new Set(quiz.value?.questions.map((q) => q.id))
    referenceFolder.value = quiz.value?.referenceFolder ?? ''
    startError.value = ''
  },
)

/**
 * Keep the limit within range and the manual selection within the limit.
 *
 * Lowering the limit below the current selection trims it back to that many
 * questions, in the quiz's own order, rather than leaving a selection that
 * reads as over the cap it is meant to respect.
 */
watch(limit, (raw) => {
  const capped = Math.min(Math.max(1, Math.floor(raw) || 1), totalQuestions.value)
  if (capped !== raw) {
    limit.value = capped
    return
  }
  if (manualSelection.value.size > capped) {
    const keep = (quiz.value?.questions ?? [])
      .filter((q) => manualSelection.value.has(q.id))
      .slice(0, capped)
      .map((q) => q.id)
    manualSelection.value = new Set(keep)
  }
})

/** Rename the open quiz set. */
async function renameQuiz(): Promise<void> {
  if (!quiz.value) return
  const newName = await askName('Rename the quiz', {
    label: 'Name',
    initial: quiz.value.name,
    confirmLabel: 'Rename',
  })
  if (newName) await tutor.renameQuiz(quiz.value.id, newName)
}

/** Toggle one question in and out of the manual selection, capped at the limit. */
function toggleManual(id: string): void {
  const set = new Set(manualSelection.value)
  if (set.has(id)) {
    set.delete(id)
  } else if (set.size < limit.value) {
    set.add(id)
  }
  manualSelection.value = set
}

/** A random permutation of an array, leaving the original untouched. */
function shuffled<T>(items: T[]): T[] {
  const copy = [...items]
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[copy[i], copy[j]] = [copy[j], copy[i]]
  }
  return copy
}

/** The question queue an attempt in the current mode/limit/selection covers. */
function buildSession(): TutorQuestion[] {
  const all = quiz.value?.questions ?? []
  const cap = Math.min(Math.max(1, Math.floor(limit.value) || 1), all.length)
  if (mode.value === 'sequential') return all.slice(0, cap)
  if (mode.value === 'random') return shuffled(all).slice(0, cap)
  return all.filter((q) => manualSelection.value.has(q.id)).slice(0, cap)
}

/** ------------------------------------------------------------------ taking -- */

const currentIndex = ref(0)
const selectedSet = ref<Set<number>>(new Set())
const confirmed = ref(false)
const results = ref<Record<string, boolean>>({})
const referenceNote = ref<Note | null>(null)
const referenceLoading = ref(false)
const referenceError = ref('')

const sessionQuestions = ref<TutorQuestion[]>([])
const currentQuestion = computed(() => sessionQuestions.value[currentIndex.value] ?? null)
const isMultiAnswer = computed(() => (currentQuestion.value?.correctIndices.length ?? 0) > 1)
const answeredCount = computed(() => Object.keys(results.value).length)
const correctCount = computed(() => Object.values(results.value).filter(Boolean).length)
const isLastQuestion = computed(() => currentIndex.value === sessionQuestions.value.length - 1)

/** Configure the attempt and start taking it. */
function startQuiz(): void {
  startError.value = ''
  const built = buildSession()
  if (mode.value === 'manual' && built.length === 0) {
    startError.value = 'Pick at least one question.'
    return
  }
  sessionQuestions.value = built
  currentIndex.value = 0
  selectedSet.value = new Set()
  confirmed.value = false
  results.value = {}
  referenceNote.value = null
  referenceError.value = ''
  noteDraft.value = ''
  cancelEditNote()
  takingSession.value = true
}

/** Jump to a question, its own attempt starting fresh. */
function goTo(index: number): void {
  currentIndex.value = index
  selectedSet.value = new Set()
  confirmed.value = false
  referenceNote.value = null
  referenceError.value = ''
  noteDraft.value = ''
  cancelEditNote()
}

/**
 * Choose an answer, only while the question is still open.
 *
 * A question with one correct answer behaves like a radio button -- picking
 * one replaces whatever was picked before; a question with several behaves
 * like a set of checkboxes, so a click there only toggles that one answer.
 */
function choose(index: number): void {
  if (confirmed.value) return
  if (!isMultiAnswer.value) {
    selectedSet.value = new Set([index])
    return
  }
  const set = new Set(selectedSet.value)
  if (set.has(index)) set.delete(index)
  else set.add(index)
  selectedSet.value = set
}

/** Lock the choice in and record whether it matches the correct answers exactly. */
function confirmAnswer(): void {
  const question = currentQuestion.value
  if (!question || selectedSet.value.size === 0) return
  confirmed.value = true
  const correct = new Set(question.correctIndices)
  const isCorrect =
    selectedSet.value.size === correct.size && [...selectedSet.value].every((index) => correct.has(index))
  results.value = { ...results.value, [question.id]: isCorrect }
}

/** Record the completed attempt and return to the quiz's detail page. */
async function finishSession(): Promise<void> {
  if (!quiz.value) return
  await tutor.recordAttempt(quiz.value.id, mode.value, sessionQuestions.value.length, correctCount.value)
  takingSession.value = false
}

/** Open one of the current question's reference notes beside it. */
async function openReference(path: string): Promise<void> {
  referenceLoading.value = true
  referenceError.value = ''
  try {
    referenceNote.value = await api.readNote(path)
  } catch (raised) {
    referenceError.value = raised instanceof ApiError ? raised.message : 'Unexpected error'
  } finally {
    referenceLoading.value = false
  }
}

function closeReference(): void {
  referenceNote.value = null
}

/** A hollow-relative path's own file name, dropping the folders it sits in. */
function fileName(path: string): string {
  return path.split('/').pop() ?? path
}

/* -------------------------------------------------------------------- notes -- */

const noteDraft = ref('')
const editingNoteId = ref<string | null>(null)
const editingNoteText = ref('')

/** Replace one question of the running session with its freshly-saved version. */
function syncSessionQuestion(updated: TutorQuestion): void {
  const index = sessionQuestions.value.findIndex((question) => question.id === updated.id)
  if (index === -1) return
  const next = [...sessionQuestions.value]
  next[index] = updated
  sessionQuestions.value = next
}

/** After a note operation, pull the question's fresh notes back into the session. */
function refreshCurrentQuestion(): void {
  const questionId = currentQuestion.value?.id
  const updated = tutor.activeQuiz.value?.questions.find((question) => question.id === questionId)
  if (updated) syncSessionQuestion(updated)
}

/** Add the drafted note to the current question. */
async function addNote(): Promise<void> {
  const question = currentQuestion.value
  const text = noteDraft.value.trim()
  if (!question || !text) return
  if (await tutor.addNote(question.id, text)) {
    noteDraft.value = ''
    refreshCurrentQuestion()
  }
}

/** Start editing one note, independently of the question's other notes. */
function startEditNote(note: TutorNote): void {
  editingNoteId.value = note.id
  editingNoteText.value = note.text
}

function cancelEditNote(): void {
  editingNoteId.value = null
  editingNoteText.value = ''
}

/** Save the note being edited. */
async function saveEditNote(): Promise<void> {
  const question = currentQuestion.value
  const noteId = editingNoteId.value
  const text = editingNoteText.value.trim()
  if (!question || !noteId || !text) return
  if (await tutor.updateNote(question.id, noteId, text)) {
    refreshCurrentQuestion()
    cancelEditNote()
  }
}

/** Delete one note, independently of the question's other notes. */
async function removeNote(noteId: string): Promise<void> {
  const question = currentQuestion.value
  if (!question) return
  const agreed = await ask('Delete this note', 'This note will be removed. This cannot be undone.', {
    confirmLabel: 'Delete',
    danger: true,
  })
  if (!agreed) return
  if (await tutor.deleteNote(question.id, noteId)) refreshCurrentQuestion()
}

/** Leave the attempt without recording it, back to the detail page. */
function abandonSession(): void {
  takingSession.value = false
}

function backToList(): void {
  tutor.closeQuiz()
}

/*
 * TutorView stays mounted the whole session (App.vue only v-shows it), so it
 * cannot rely on onMounted to load the quiz list: that would run once, at
 * app start, before the tutor feature is necessarily on -- and never again,
 * leaving a stale "not enabled" error on screen even after the feature is
 * turned on and the sidebar link clicked. Reloading every time the view is
 * switched to keeps it current instead.
 */
watch(view, (current) => {
  if (current !== 'tutor') return
  tutor.clearError()
  void tutor.loadQuizzes()
})
</script>

<template>
  <div class="tutor-view">
    <!-- ------------------------------------------------------------ mapping -- -->
    <div v-if="tutor.pendingImport.value" class="tutor-mapping">
      <h2>Map "{{ tutor.pendingImport.value.filename }}"</h2>
      <p class="tutor-hint">Pick which column of the spreadsheet is which.</p>

      <label class="dialog-label" for="tutor-name">Quiz name</label>
      <input id="tutor-name" v-model="name" class="dialog-field" type="text" />

      <label class="dialog-label" for="tutor-question">Question</label>
      <select id="tutor-question" v-model="questionColumn" class="dialog-field">
        <option v-for="column in tutor.pendingImport.value.columns" :key="column" :value="column">
          {{ column }}
        </option>
      </select>

      <span class="dialog-label">Answers (pick at least two)</span>
      <div class="tutor-checkboxes">
        <label v-for="column in tutor.pendingImport.value.columns" :key="column" class="tutor-checkbox">
          <input v-model="answerColumns" type="checkbox" :value="column" />
          {{ column }}
        </label>
      </div>

      <label class="dialog-label" for="tutor-correct">Correct answer</label>
      <select id="tutor-correct" v-model="correctColumn" class="dialog-field">
        <option v-for="column in tutor.pendingImport.value.columns" :key="column" :value="column">
          {{ column }}
        </option>
      </select>

      <label class="dialog-label" for="tutor-reference">Reference (optional)</label>
      <select id="tutor-reference" v-model="referenceColumn" class="dialog-field">
        <option value="">None</option>
        <option v-for="column in tutor.pendingImport.value.columns" :key="column" :value="column">
          {{ column }}
        </option>
      </select>

      <template v-if="referenceColumn">
        <label class="tutor-checkbox tutor-multi-reference">
          <input v-model="multiReference" type="checkbox" />
          A cell may name more than one reference
        </label>
        <template v-if="multiReference">
          <label class="dialog-label" for="tutor-reference-separator">Separator between references</label>
          <input
            id="tutor-reference-separator"
            v-model="referenceSeparator"
            class="dialog-field tutor-limit-field"
            type="text"
            placeholder=";"
          />
        </template>
      </template>

      <label class="tutor-checkbox tutor-multi-reference">
        <input v-model="includeImages" type="checkbox" />
        Include images
      </label>

      <template v-if="includeImages">
        <label class="dialog-label" for="tutor-image-column">
          Column naming each image (usually the question itself)
        </label>
        <select id="tutor-image-column" v-model="imageColumn" class="dialog-field">
          <option v-for="column in tutor.pendingImport.value.columns" :key="column" :value="column">
            {{ column }}
          </option>
        </select>

        <label class="dialog-label" for="tutor-images">Images</label>
        <input
          id="tutor-images"
          class="dialog-field"
          type="file"
          accept="image/*"
          multiple
          @change="onImagesChosen"
        />
        <p class="tutor-hint">
          {{ imageFiles.length }} image{{ imageFiles.length === 1 ? '' : 's' }} chosen -- each one is
          matched to every row whose column above names it.
        </p>
      </template>

      <div class="tutor-preview">
        <table>
          <thead>
            <tr>
              <th v-for="column in tutor.pendingImport.value.columns" :key="column">{{ column }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, index) in tutor.pendingImport.value.previewRows" :key="index">
              <td v-for="(cell, cellIndex) in row" :key="cellIndex">{{ cell }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <p v-if="mappingError || tutor.error.value" class="field-error">
        {{ mappingError || tutor.error.value }}
      </p>

      <div class="dialog-actions">
        <button type="button" class="button" @click="tutor.cancelImport()">Cancel</button>
        <button type="button" class="button button-primary" @click="submitMapping()">
          Create quiz
        </button>
      </div>
    </div>

    <!-- ------------------------------------------------------------- taking -- -->
    <div v-else-if="quiz && takingSession" class="tutor-quiz" :class="{ 'has-reference': referenceNote }">
      <aside class="tutor-question-nav">
        <button type="button" class="button button-small" @click="abandonSession()">
          ← Back to details
        </button>
        <h3 class="tutor-quiz-title">{{ quiz.name }}</h3>
        <p class="tutor-hint">{{ correctCount }} / {{ answeredCount }} correct so far</p>
        <ol class="tutor-question-list">
          <li v-for="(question, index) in sessionQuestions" :key="question.id">
            <button
              type="button"
              class="tutor-question-nav-item"
              :class="{
                'is-active': index === currentIndex,
                'is-correct': results[question.id] === true,
                'is-incorrect': results[question.id] === false,
              }"
              @click="goTo(index)"
            >
              {{ index + 1 }}
            </button>
          </li>
        </ol>
      </aside>

      <div class="tutor-question-pane">
        <article v-if="currentQuestion" class="tutor-question">
          <p class="tutor-question-count">
            Question {{ currentIndex + 1 }} of {{ sessionQuestions.length }}
          </p>
          <h2 class="tutor-question-text">{{ currentQuestion.question }}</h2>

          <div v-if="currentQuestion.imagePaths.length" class="tutor-question-images">
            <img
              v-for="path in currentQuestion.imagePaths"
              :key="path"
              :src="`/tutor-images/${path}`"
              :alt="currentQuestion.question"
            />
          </div>

          <p v-if="isMultiAnswer" class="tutor-hint">Select all that apply.</p>

          <ul class="tutor-answers">
            <li v-for="(answer, index) in currentQuestion.answers" :key="index">
              <button
                type="button"
                class="tutor-answer"
                :class="{
                  'is-selected': selectedSet.has(index) && !confirmed,
                  'is-correct': confirmed && currentQuestion.correctIndices.includes(index),
                  'is-incorrect':
                    confirmed && selectedSet.has(index) && !currentQuestion.correctIndices.includes(index),
                }"
                :disabled="confirmed"
                @click="choose(index)"
              >
                {{ answer }}
              </button>
            </li>
          </ul>

          <div class="dialog-actions tutor-question-actions">
            <button
              v-if="!confirmed"
              type="button"
              class="button button-primary"
              :disabled="selectedSet.size === 0"
              @click="confirmAnswer()"
            >
              Confirm
            </button>
            <template v-else>
              <div v-if="currentQuestion.referencePaths.length" class="tutor-reference-buttons">
                <button
                  v-for="path in currentQuestion.referencePaths"
                  :key="path"
                  type="button"
                  class="button"
                  :title="path"
                  @click="openReference(path)"
                >
                  📖 {{ fileName(path) }}
                </button>
              </div>
              <span v-else-if="currentQuestion.reference" class="tutor-hint">
                Reference "{{ currentQuestion.reference }}" was not found in the hollow.
              </span>
              <button
                v-if="!isLastQuestion"
                type="button"
                class="button button-primary"
                @click="goTo(currentIndex + 1)"
              >
                Next question →
              </button>
              <button v-else type="button" class="button button-primary" @click="finishSession()">
                🏁 Finish
              </button>
            </template>
          </div>

          <p v-if="referenceLoading" class="tutor-hint">Loading the reference…</p>
          <p v-if="referenceError" class="field-error">{{ referenceError }}</p>

          <section v-if="confirmed && currentQuestion" class="tutor-notes">
            <h3 class="tutor-section-title">Notes</h3>
            <ul v-if="currentQuestion.notes.length" class="tutor-note-list">
              <li v-for="note in currentQuestion.notes" :key="note.id" class="tutor-note">
                <template v-if="editingNoteId === note.id">
                  <textarea v-model="editingNoteText" class="dialog-field tutor-note-field" rows="2" />
                  <div class="tutor-note-actions">
                    <button type="button" class="button button-small" @click="cancelEditNote()">
                      Cancel
                    </button>
                    <button
                      type="button"
                      class="button button-small button-primary"
                      :disabled="!editingNoteText.trim()"
                      @click="saveEditNote()"
                    >
                      Save
                    </button>
                  </div>
                </template>
                <template v-else>
                  <p class="tutor-note-text">{{ note.text }}</p>
                  <div class="tutor-note-actions">
                    <button type="button" class="icon-button" title="Edit this note" @click="startEditNote(note)">
                      ✏️
                    </button>
                    <button
                      type="button"
                      class="icon-button"
                      title="Delete this note"
                      @click="removeNote(note.id)"
                    >
                      🗑️
                    </button>
                  </div>
                </template>
              </li>
            </ul>
            <p v-else class="tutor-hint">No notes yet.</p>

            <div class="tutor-note-new">
              <textarea
                v-model="noteDraft"
                class="dialog-field tutor-note-field"
                rows="2"
                placeholder="Add a note about this question…"
              />
              <button
                type="button"
                class="button button-small"
                :disabled="!noteDraft.trim()"
                @click="addNote()"
              >
                Add note
              </button>
            </div>
          </section>
        </article>
      </div>

      <div v-if="referenceNote" class="tutor-reference-pane">
        <div class="tutor-reference-header">
          <span class="tutor-reference-title">{{ referenceNote.path }}</span>
          <button type="button" class="icon-button" title="Close the reference" @click="closeReference()">
            ✕
          </button>
        </div>
        <article class="note-preview markdown-body tutor-reference-body" v-html="referenceNote.html" />
      </div>
    </div>

    <!-- -------------------------------------------------------------- detail -- -->
    <div v-else-if="quiz" class="tutor-detail">
      <button type="button" class="button button-small" @click="backToList()">← Quizzes</button>

      <div class="tutor-detail-header">
        <h2>{{ quiz.name }}</h2>
        <button type="button" class="icon-button" title="Rename this quiz" @click="renameQuiz()">
          ✏️
        </button>
      </div>

      <div class="tutor-stats">
        <div class="tutor-stat">
          <span class="tutor-stat-value">{{ totalQuestions }}</span>
          <span class="tutor-stat-label">questions</span>
        </div>
        <div class="tutor-stat">
          <span class="tutor-stat-value">{{ attemptCount }}</span>
          <span class="tutor-stat-label">attempts</span>
        </div>
        <div class="tutor-stat">
          <span class="tutor-stat-value">{{ bestScore !== null ? pct(bestScore) : '—' }}</span>
          <span class="tutor-stat-label">best score</span>
        </div>
        <div class="tutor-stat">
          <span class="tutor-stat-value">
            {{ lastAttempt ? pct(lastAttempt.correctCount / lastAttempt.questionCount) : '—' }}
          </span>
          <span class="tutor-stat-label">last score</span>
        </div>
      </div>

      <template v-if="referenceCount > 0">
        <h3 class="tutor-section-title">References</h3>
        <label class="dialog-label" for="tutor-reference-folder">
          Search for references in
        </label>
        <select
          id="tutor-reference-folder"
          v-model="referenceFolder"
          class="dialog-field tutor-limit-field"
          @change="applyReferenceFolder()"
        >
          <option value="">Whole hollow</option>
          <option v-for="folder in folderOptions" :key="folder.path" :value="folder.path">
            {{ folder.label }}
          </option>
        </select>
        <p class="tutor-hint">
          {{ resolvedReferenceCount }} / {{ referenceCount }} references resolved, subfolders
          included.
        </p>
      </template>

      <h3 class="tutor-section-title">Start an attempt</h3>

      <div class="tutor-mode-select">
        <label class="tutor-mode-card" :class="{ 'is-selected': mode === 'sequential' }">
          <input v-model="mode" type="radio" value="sequential" name="tutor-mode" />
          <span class="tutor-mode-title">Sequential</span>
          <span class="tutor-mode-desc">Questions in the order of the file.</span>
        </label>
        <label class="tutor-mode-card" :class="{ 'is-selected': mode === 'random' }">
          <input v-model="mode" type="radio" value="random" name="tutor-mode" />
          <span class="tutor-mode-title">Random</span>
          <span class="tutor-mode-desc">Shuffled order, a new one each time.</span>
        </label>
        <label class="tutor-mode-card" :class="{ 'is-selected': mode === 'manual' }">
          <input v-model="mode" type="radio" value="manual" name="tutor-mode" />
          <span class="tutor-mode-title">Manual pick</span>
          <span class="tutor-mode-desc">Choose exactly which questions to take.</span>
        </label>
      </div>

      <label class="dialog-label" for="tutor-limit">
        How many questions (up to {{ totalQuestions }})
      </label>
      <input
        id="tutor-limit"
        v-model.number="limit"
        class="dialog-field tutor-limit-field"
        type="number"
        min="1"
        :max="totalQuestions"
      />

      <div v-if="mode === 'manual'" class="tutor-manual-picker">
        <p class="tutor-hint">{{ manualSelection.size }} / {{ limit }} selected</p>
        <ul class="tutor-manual-list">
          <li v-for="question in quiz.questions" :key="question.id">
            <label class="tutor-manual-item">
              <input
                type="checkbox"
                :checked="manualSelection.has(question.id)"
                :disabled="!manualSelection.has(question.id) && manualSelection.size >= limit"
                @change="toggleManual(question.id)"
              />
              {{ question.question }}
            </label>
          </li>
        </ul>
      </div>

      <p v-if="startError || tutor.error.value" class="field-error">
        {{ startError || tutor.error.value }}
      </p>

      <div class="dialog-actions">
        <button type="button" class="button button-primary" @click="startQuiz()">▶️ Start</button>
      </div>
    </div>

    <!-- --------------------------------------------------------------- list -- -->
    <div v-else class="tutor-list-view">
      <div class="tutor-list-header">
        <h2>DragonGlass Tutor</h2>
        <button type="button" class="button button-primary" @click="fileInput?.click()">
          📥 Import spreadsheet
        </button>
        <input
          ref="fileInput"
          class="hidden-input"
          type="file"
          accept=".csv,.xlsx"
          @change="onFileChosen"
        />
      </div>

      <p v-if="tutor.error.value" class="sidebar-error" @click="tutor.clearError()">
        {{ tutor.error.value }}
      </p>

      <p v-if="!tutor.loading.value && !tutor.quizzes.value.length" class="tree-empty">
        No quizzes yet. Import a .csv or .xlsx to build one — you will be asked which column is the
        question, which are the answers, which one is correct, and which holds a reference note.
      </p>

      <ul v-else class="tutor-quiz-list">
        <li v-for="quizSummary in tutor.quizzes.value" :key="quizSummary.id" class="tutor-quiz-card">
          <button type="button" class="tutor-quiz-card-open" @click="tutor.openQuiz(quizSummary.id)">
            <span class="tutor-quiz-card-name">{{ quizSummary.name }}</span>
            <span class="tutor-quiz-card-meta">{{ quizSummary.questionCount }} questions</span>
          </button>
          <button
            type="button"
            class="icon-button"
            title="Delete this quiz"
            @click="removeQuiz(quizSummary.id, quizSummary.name)"
          >
            🗑️
          </button>
        </li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.tutor-view {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
  overflow: auto;
}

.tutor-hint {
  margin: 0;
  color: var(--text-muted);
  font-size: 12.5px;
}

/* -- import & mapping -- */

.tutor-mapping {
  display: flex;
  flex-direction: column;
  max-width: 640px;
  padding: 24px 28px;
  overflow: auto;
}

.tutor-mapping h2 {
  margin: 0 0 4px;
  font-size: 17px;
}

.tutor-mapping .dialog-label {
  margin-top: 12px;
}

.tutor-multi-reference {
  margin-top: 8px;
}

.tutor-checkboxes {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 16px;
  margin-bottom: 4px;
}

.tutor-checkbox {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--text);
  font-size: 13px;
}

.tutor-preview {
  margin: 16px 0;
  overflow: auto;
  border: 1px solid var(--border);
  border-radius: var(--radius);
}

.tutor-preview table {
  border-collapse: collapse;
  font-size: 12.5px;
  white-space: nowrap;
}

.tutor-preview th,
.tutor-preview td {
  padding: 5px 10px;
  border-bottom: 1px solid var(--border);
  text-align: left;
}

.tutor-preview th {
  background: var(--bg-sunken);
  color: var(--text-muted);
}

/* -- quiz list -- */

.tutor-list-view {
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding: 24px 28px;
  overflow: auto;
}

.tutor-list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.tutor-list-header h2 {
  margin: 0;
  font-size: 17px;
}

.tutor-quiz-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.tutor-quiz-card {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px;
  background: var(--bg-panel);
  border: 1px solid var(--border);
  border-radius: var(--radius);
}

.tutor-quiz-card-open {
  display: flex;
  flex: 1;
  align-items: baseline;
  gap: 10px;
  padding: 8px 10px;
  background: none;
  border: none;
  color: var(--text);
  cursor: pointer;
  font: inherit;
  text-align: left;
}

.tutor-quiz-card-name {
  font-size: 13.5px;
}

.tutor-quiz-card-meta {
  color: var(--text-muted);
  font-size: 12px;
}

/* -- taking a quiz -- */

.tutor-quiz {
  display: grid;
  grid-template-columns: 200px minmax(0, 1fr);
  flex: 1;
  min-height: 0;
}

.tutor-quiz.has-reference {
  grid-template-columns: 200px minmax(0, 1fr) minmax(0, 1fr);
}

.tutor-question-nav {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 16px;
  background: var(--bg-panel);
  border-right: 1px solid var(--border);
  overflow: auto;
}

.tutor-quiz-title {
  margin: 4px 0 0;
  font-size: 14px;
}

.tutor-question-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 4px 0 0;
  padding: 0;
  list-style: none;
}

.tutor-question-nav-item {
  width: 28px;
  height: 28px;
  padding: 0;
  background: var(--bg-sunken);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--text);
  cursor: pointer;
  font: inherit;
  font-size: 12px;
}

.tutor-question-nav-item:hover {
  background: var(--bg-hover);
}

.tutor-question-nav-item.is-active {
  border-color: var(--accent);
}

.tutor-question-nav-item.is-correct {
  background: color-mix(in srgb, #2e7d32 24%, transparent);
  border-color: #2e7d32;
}

.tutor-question-nav-item.is-incorrect {
  background: color-mix(in srgb, var(--danger) 22%, transparent);
  border-color: var(--danger);
}

.tutor-question-pane {
  display: flex;
  flex-direction: column;
  min-width: 0;
  padding: 24px 28px;
  overflow: auto;
}

.tutor-question {
  max-width: 640px;
}

.tutor-question-count {
  margin: 0 0 4px;
  color: var(--text-muted);
  font-size: 12.5px;
}

.tutor-question-text {
  margin: 0 0 18px;
  font-size: 18px;
}

.tutor-question-images {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 18px;
}

.tutor-question-images img {
  max-width: 100%;
  max-height: 320px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
}

.tutor-answers {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin: 0 0 18px;
  padding: 0;
  list-style: none;
}

.tutor-answer {
  width: 100%;
  padding: 10px 14px;
  background: var(--bg-sunken);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--text);
  cursor: pointer;
  font: inherit;
  text-align: left;
}

.tutor-answer:hover:not(:disabled) {
  background: var(--bg-hover);
}

.tutor-answer:disabled {
  cursor: default;
}

.tutor-answer.is-selected {
  background: var(--bg-selected);
  border-color: var(--accent);
}

.tutor-answer.is-correct {
  background: color-mix(in srgb, #2e7d32 20%, transparent);
  border-color: #2e7d32;
}

.tutor-answer.is-incorrect {
  background: color-mix(in srgb, var(--danger) 18%, transparent);
  border-color: var(--danger);
}

.tutor-question-actions {
  flex-direction: column;
  align-items: stretch;
  margin-bottom: 12px;
}

.tutor-question-actions > .button {
  width: 100%;
}

.tutor-reference-buttons {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.tutor-reference-buttons > .button {
  width: 100%;
  text-align: left;
}

.tutor-reference-pane {
  display: flex;
  flex-direction: column;
  min-width: 0;
  border-left: 1px solid var(--border);
  overflow: hidden;
}

.tutor-reference-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: var(--bg-panel);
  border-bottom: 1px solid var(--border);
}

.tutor-reference-title {
  overflow: hidden;
  color: var(--text-muted);
  font-size: 12.5px;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.tutor-reference-body {
  padding: 16px 20px;
  overflow: auto;
}

/* -- notes -- */

.tutor-notes {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--border);
}

.tutor-note-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin: 0 0 12px;
  padding: 0;
  list-style: none;
}

.tutor-note {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  padding: 8px 10px;
  background: var(--bg-panel);
  border: 1px solid var(--border);
  border-radius: var(--radius);
}

.tutor-note-text {
  margin: 0;
  overflow-wrap: anywhere;
  font-size: 13px;
  white-space: pre-wrap;
}

.tutor-note-actions {
  display: flex;
  flex-shrink: 0;
  gap: 4px;
}

.tutor-note-field {
  width: 100%;
  resize: vertical;
}

.tutor-note-new {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* -- quiz detail -- */

.tutor-detail {
  display: flex;
  flex-direction: column;
  max-width: 640px;
  padding: 24px 28px;
  overflow: auto;
}

.tutor-detail-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 14px 0 18px;
}

.tutor-detail-header h2 {
  margin: 0;
  font-size: 19px;
}

.tutor-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin-bottom: 24px;
}

.tutor-stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 10px 12px;
  background: var(--bg-panel);
  border: 1px solid var(--border);
  border-radius: var(--radius);
}

.tutor-stat-value {
  font-size: 18px;
  font-weight: 600;
}

.tutor-stat-label {
  color: var(--text-muted);
  font-size: 11.5px;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.tutor-section-title {
  margin: 0 0 10px;
  font-size: 14px;
}

.tutor-mode-select {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-bottom: 16px;
}

.tutor-mode-card {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px;
  background: var(--bg-sunken);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  cursor: pointer;
}

.tutor-mode-card:hover {
  background: var(--bg-hover);
}

.tutor-mode-card.is-selected {
  background: var(--bg-selected);
  border-color: var(--accent);
}

.tutor-mode-card input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

.tutor-mode-title {
  font-size: 13.5px;
  font-weight: 600;
}

.tutor-mode-desc {
  color: var(--text-muted);
  font-size: 12px;
}

.tutor-limit-field {
  max-width: 140px;
}

.tutor-manual-picker {
  margin: 4px 0 16px;
}

.tutor-manual-list {
  max-height: 220px;
  margin: 6px 0 0;
  padding: 4px 0;
  overflow: auto;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  list-style: none;
}

.tutor-manual-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 6px 10px;
  color: var(--text);
  font-size: 12.5px;
  cursor: pointer;
}

.tutor-manual-item:has(input:disabled) {
  color: var(--text-muted);
  cursor: default;
}

.tutor-manual-item input {
  margin-top: 2px;
}
</style>
