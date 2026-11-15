/// <reference lib="webworker" />
/**
 * Runs the 8-bit model in the visitor's browser (transformers.js + ONNX Runtime Web), off the main
 * thread. The model files (about 280 MB) are downloaded once from the Hugging Face Hub and cached
 * by the browser; the invoice image never leaves the device.
 */
import { AutoProcessor, AutoTokenizer, RawImage, VisionEncoderDecoderModel } from '@huggingface/transformers'
import { cleanGenerated, parseAnswer, qaPrompt, TASK_INVOICE, token2json } from './donut.ts'

export const MODEL_REPO = 'okba-bouziane/invoicedesk-donut'

export type WorkerRequest = { id: number; task: 'extract' | 'ask'; image: Blob; question?: string }
export type WorkerReply =
  | { id: number; ok: true; text?: string; fields?: Record<string, unknown>; seconds: number }
  | { id: number; ok: false; error: string }
  | { progress: { loaded: number; total: number } }

type Loaded = {
  processor: Awaited<ReturnType<typeof AutoProcessor.from_pretrained>>
  tokenizer: Awaited<ReturnType<typeof AutoTokenizer.from_pretrained>>
  model: Awaited<ReturnType<typeof VisionEncoderDecoderModel.from_pretrained>>
}
let loading: Promise<Loaded> | null = null
const files = new Map<string, { loaded: number; total: number }>()

function progress_callback(p: { status: string; file?: string; loaded?: number; total?: number }) {
  if (p.status !== 'progress' || !p.file) return
  files.set(p.file, { loaded: p.loaded ?? 0, total: p.total ?? 0 })
  const all = [...files.values()]
  self.postMessage({ progress: { loaded: all.reduce((a, f) => a + f.loaded, 0), total: all.reduce((a, f) => a + f.total, 0) } })
}

function load(): Promise<Loaded> {
  loading ??= (async () => {
    const [processor, tokenizer, model] = await Promise.all([
      AutoProcessor.from_pretrained(MODEL_REPO),
      AutoTokenizer.from_pretrained(MODEL_REPO),
      VisionEncoderDecoderModel.from_pretrained(MODEL_REPO, { dtype: 'q8', progress_callback }),
    ])
    return { processor, tokenizer, model }
  })()
  return loading
}

async function generate({ processor, tokenizer, model }: Loaded, image: Blob, prompt: string): Promise<string> {
  const { pixel_values } = await processor(await RawImage.fromBlob(image))
  const decoder_input_ids = tokenizer(prompt, { add_special_tokens: false }).input_ids
  const out = await model.generate({
    inputs: pixel_values,
    decoder_input_ids,
    max_length: 512,
    bad_words_ids: [[tokenizer.unk_token_id as number]],
  } as Parameters<typeof model.generate>[0])
  return tokenizer.batch_decode(out as Parameters<typeof tokenizer.batch_decode>[0])[0] ?? ''
}

self.addEventListener('message', async (e: MessageEvent<WorkerRequest>) => {
  const { id, task, image, question } = e.data
  try {
    const loaded = await load()
    const t0 = performance.now()
    if (task === 'extract') {
      const seq = await generate(loaded, image, TASK_INVOICE)
      const tok = loaded.tokenizer
      const fields = token2json(cleanGenerated(seq, tok.eos_token ?? '</s>', tok.pad_token ?? '<pad>'))
      self.postMessage({ id, ok: true, fields, seconds: (performance.now() - t0) / 1000 } satisfies WorkerReply)
    } else {
      const seq = await generate(loaded, image, qaPrompt((question ?? '').trim()))
      self.postMessage({ id, ok: true, text: parseAnswer(seq), seconds: (performance.now() - t0) / 1000 } satisfies WorkerReply)
    }
  } catch (err) {
    self.postMessage({ id, ok: false, error: err instanceof Error ? err.message : String(err) } satisfies WorkerReply)
  }
})
