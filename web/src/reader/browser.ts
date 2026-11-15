/**
 * The browser reader: same results as the API (ExtractResult / AskResult), computed in a Web Worker
 * with the same parsing, tidy() and checks as the Python code (see parity.test.ts).
 */
import type { AskResult, ExtractResult } from '../lib/api.ts'
import { checks, tidy, typed } from './normalize.ts'
import type { WorkerReply, WorkerRequest } from './worker.ts'

const MODEL_NAME = 'invoicedesk-donut (8-bit, in your browser)'
type Listener = (p: { loaded: number; total: number }) => void

let worker: Worker | null = null
let nextId = 1
const pending = new Map<number, { resolve: (r: WorkerReply) => void }>()
const listeners = new Set<Listener>()

function getWorker(): Worker {
  if (!worker) {
    worker = new Worker(new URL('./worker.ts', import.meta.url), { type: 'module' })
    worker.addEventListener('message', (e: MessageEvent<WorkerReply>) => {
      const msg = e.data
      if ('progress' in msg) return listeners.forEach((l) => l(msg.progress))
      pending.get(msg.id)?.resolve(msg)
      pending.delete(msg.id)
    })
  }
  return worker
}

/** Download progress of the model files (first use only; the browser caches them). */
export function onModelProgress(listener: Listener): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

function call(req: Omit<WorkerRequest, 'id'>): Promise<WorkerReply> {
  const id = nextId++
  return new Promise((resolve) => {
    pending.set(id, { resolve })
    getWorker().postMessage({ ...req, id })
  })
}

export async function extractInBrowser(image: Blob): Promise<ExtractResult> {
  const r = await call({ task: 'extract', image })
  if ('progress' in r || !r.ok) throw new Error('progress' in r ? 'unexpected' : r.error)
  const fields = tidy(r.fields)
  return { model: MODEL_NAME, fields, typed: typed(fields), checks: checks(fields), seconds: Math.round(r.seconds * 100) / 100 }
}

export async function askInBrowser(image: Blob, question: string): Promise<AskResult> {
  const r = await call({ task: 'ask', image, question })
  if ('progress' in r || !r.ok) throw new Error('progress' in r ? 'unexpected' : r.error)
  return { model: MODEL_NAME, question: question.trim(), answer: r.text ?? '', seconds: Math.round(r.seconds * 100) / 100 }
}
