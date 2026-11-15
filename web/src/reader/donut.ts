/** TypeScript twin of invoicedesk/donut.py: the task prompts and the token-sequence parser. */

export const TASK_INVOICE = '<s_dzinv>'
const SEP = '<sep/>'

export type Parsed = { [key: string]: Parsed | Parsed[] | string | string[] } | Parsed[] | string

const escape = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

/** Parse a generated sequence back into JSON; tolerant of a truncated or malformed tail. */
export function token2json(input: string): Record<string, unknown> {
  const out: Record<string, unknown> = {}
  let seq = input.trim()
  while (seq) {
    const start = /<s_(.*?)>/.exec(seq)
    if (!start) break
    const key = start[1] ?? ''
    const end = new RegExp(`</s_${escape(key)}>`).exec(seq)
    if (!end) {
      seq = seq.replace(start[0], '') // unclosed: drop this opening tag and keep going
      continue
    }
    const inner = seq.slice(start.index + start[0].length, end.index)
    let value: unknown
    if (/<s_.*?>/.test(inner)) {
      const parts = inner.split(SEP).map(token2json).filter((p) => Object.keys(p).length > 0)
      value = parts.length > 1 || key === 'items' ? parts : (parts[0] ?? {})
    } else {
      const items = inner.split(SEP).map((p) => p.trim())
      value = items.length > 1 ? items : items[0]
    }
    if (key in out) {
      const prev = out[key]
      out[key] = [...(Array.isArray(prev) ? prev : [prev]), ...(Array.isArray(value) ? value : [value])]
    } else {
      out[key] = value
    }
    seq = seq.slice(end.index + end[0].length).trim()
  }
  return out
}

export const qaPrompt = (question: string) => `<s_docvqa><s_question>${question}</s_question><s_answer>`

export function parseAnswer(seq: string): string {
  return (/<s_answer>([\s\S]*?)(?:<\/s_answer>|$)/.exec(seq)?.[1] ?? '').trim()
}

/** Drop special tokens added by generation and the leading task token. */
export function cleanGenerated(seq: string, eos: string, pad: string): string {
  return seq.split(eos).join('').split(pad).join('').replace(/^\s*<s_(cord-v2|dzinv)>/, '').trim()
}
