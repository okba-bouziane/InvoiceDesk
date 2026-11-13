import type { AskResult, ExtractResult } from './api.ts'

/** Notes are stored as codes, so switching the language re-words the whole conversation. */
export type NoteCode = 'notImage' | 'tooBig' | 'needInvoice' | 'offline' | 'unexpected' | 'status'

export type Message =
  | { id: number; role: 'user'; kind: 'invoice'; url: string; name: string }
  | { id: number; role: 'user'; kind: 'question'; text: string }
  | { id: number; role: 'bot'; kind: 'pending'; task: 'reading' | 'searching' }
  | { id: number; role: 'bot'; kind: 'extract'; result: ExtractResult }
  | { id: number; role: 'bot'; kind: 'answer'; result: AskResult }
  | { id: number; role: 'bot'; kind: 'note'; code: NoteCode; error?: boolean; status?: number; detail?: string }

export type NewMessage = Message extends infer M ? (M extends Message ? Omit<M, 'id'> : never) : never

export interface Invoice {
  blob: Blob
  url: string
  name: string
}

/** One chat is about one invoice. History lives only in memory: a refresh clears it. */
export interface Chat {
  id: string
  createdAt: number
  invoice: Invoice | null
  /** Filled once the invoice is read: supplier and total, for the history list. */
  vendor?: string
  total?: string
  /** True when a check on the extracted totals failed. */
  review?: boolean
  messages: Message[]
}

export interface State {
  nextMessage: number
  chats: Chat[] // newest first
  activeId: string | null // null: the empty "new chat" screen
}

export type Action =
  | { type: 'newChat' }
  | { type: 'select'; chatId: string }
  | { type: 'remove'; chatId: string }
  | { type: 'start'; chatId: string; invoice: Invoice | null; at: number }
  | { type: 'add'; chatId: string; message: NewMessage }
  | { type: 'resolve'; chatId: string; id: number; message: NewMessage }
  | { type: 'label'; chatId: string; vendor?: string; total?: string; review?: boolean }

export const initial: State = { nextMessage: 1, chats: [], activeId: null }

function update(state: State, chatId: string, fn: (c: Chat) => Chat): Chat[] {
  return state.chats.map((c) => (c.id === chatId ? fn(c) : c))
}

export function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'newChat':
      return { ...state, activeId: null }
    case 'select':
      return state.chats.some((c) => c.id === action.chatId) ? { ...state, activeId: action.chatId } : state
    case 'remove': {
      const chats = state.chats.filter((c) => c.id !== action.chatId)
      return { ...state, chats, activeId: state.activeId === action.chatId ? null : state.activeId }
    }
    case 'start':
      return {
        ...state,
        chats: [{ id: action.chatId, createdAt: action.at, invoice: action.invoice, messages: [] }, ...state.chats],
        activeId: action.chatId,
      }
    case 'add': {
      const message = { ...action.message, id: state.nextMessage } as Message
      return {
        ...state,
        nextMessage: state.nextMessage + 1,
        chats: update(state, action.chatId, (c) => ({ ...c, messages: [...c.messages, message] })),
      }
    }
    case 'resolve':
      return {
        ...state,
        chats: update(state, action.chatId, (c) => ({
          ...c,
          messages: c.messages.map((m) => (m.id === action.id ? ({ ...action.message, id: m.id } as Message) : m)),
        })),
      }
    case 'label':
      return { ...state, chats: update(state, action.chatId, (c) => ({ ...c, vendor: action.vendor, total: action.total, review: action.review })) }
  }
}
