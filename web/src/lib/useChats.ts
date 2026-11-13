import { useMutation } from '@tanstack/react-query'
import { useCallback, useEffect, useReducer, useRef } from 'react'
import { MAX_BYTES } from '../config.ts'
import { ApiError, askInvoice, extractInvoice } from './api.ts'
import { initial, reducer, type Chat, type NewMessage } from './conversation.ts'

function failure(err: Error): NewMessage {
  if (err instanceof ApiError) {
    return { role: 'bot', kind: 'note', error: true, code: err.code, status: err.status, detail: err.detail }
  }
  return { role: 'bot', kind: 'note', error: true, code: 'unexpected' }
}

let chatCounter = 0
const newChatId = () => `chat-${Date.now().toString(36)}-${(chatCounter += 1)}`

/**
 * Chats of this browser tab, kept in memory only (nothing is stored on the server or on disk,
 * so a refresh clears the history). Each chat is about one invoice.
 */
export function useChats() {
  const [state, dispatch] = useReducer(reducer, initial)
  // Every message goes through `add`, so this counter stays equal to the reducer's `nextMessage`;
  // keeping it in a ref lets a handler know the id of the message it just added.
  const nextId = useRef(initial.nextMessage)
  const chatsRef = useRef<Chat[]>([])
  useEffect(() => {
    chatsRef.current = state.chats
  }, [state.chats])
  // Free the image previews when the tab closes.
  useEffect(() => () => chatsRef.current.forEach((c) => c.invoice && URL.revokeObjectURL(c.invoice.url)), [])

  const add = useCallback((chatId: string, message: NewMessage) => {
    const id = nextId.current
    nextId.current += 1
    dispatch({ type: 'add', chatId, message })
    return id
  }, [])

  const extract = useMutation({ mutationFn: extractInvoice })
  const ask = useMutation({ mutationFn: ({ blob, question }: { blob: Blob; question: string }) => askInvoice(blob, question) })
  const busy = extract.isPending || ask.isPending
  const active = state.chats.find((c) => c.id === state.activeId) ?? null

  /** Sending an invoice always starts a new chat. */
  const sendInvoice = useCallback(
    (blob: Blob, name: string) => {
      if (busy) return
      const chatId = newChatId()
      const problem = !/^image\/(jpeg|png)$/.test(blob.type) ? 'notImage' : blob.size > MAX_BYTES ? 'tooBig' : null
      if (problem) {
        // keep the current chat if there is one; otherwise show the error in a fresh chat
        const target = active?.id ?? chatId
        if (!active) dispatch({ type: 'start', chatId, invoice: null, at: Date.now() })
        add(target, { role: 'bot', kind: 'note', error: true, code: problem })
        return
      }
      const invoice = { blob, url: URL.createObjectURL(blob), name }
      dispatch({ type: 'start', chatId, invoice, at: Date.now() })
      add(chatId, { role: 'user', kind: 'invoice', url: invoice.url, name })
      const pending = add(chatId, { role: 'bot', kind: 'pending', task: 'reading' })
      extract.mutate(blob, {
        onSuccess: (result) => {
          dispatch({ type: 'resolve', chatId, id: pending, message: { role: 'bot', kind: 'extract', result } })
          dispatch({
            type: 'label',
            chatId,
            vendor: result.fields.vendor,
            total: result.fields.total_ttc,
            review: result.checks.some((c) => !c.ok),
          })
        },
        onError: (err) => dispatch({ type: 'resolve', chatId, id: pending, message: failure(err) }),
      })
    },
    [active, add, busy, extract],
  )

  const sendQuestion = useCallback(
    (question: string) => {
      const q = question.trim()
      if (!q || busy) return
      let chatId = active?.id
      if (!chatId) {
        chatId = newChatId()
        dispatch({ type: 'start', chatId, invoice: null, at: Date.now() })
      }
      add(chatId, { role: 'user', kind: 'question', text: q })
      if (!active?.invoice) {
        add(chatId, { role: 'bot', kind: 'note', code: 'needInvoice' })
        return
      }
      const pending = add(chatId, { role: 'bot', kind: 'pending', task: 'searching' })
      const target = chatId
      ask.mutate(
        { blob: active.invoice.blob, question: q },
        {
          onSuccess: (result) => dispatch({ type: 'resolve', chatId: target, id: pending, message: { role: 'bot', kind: 'answer', result } }),
          onError: (err) => dispatch({ type: 'resolve', chatId: target, id: pending, message: failure(err) }),
        },
      )
    },
    [active, add, ask, busy],
  )

  const removeChat = useCallback((chatId: string) => {
    const chat = chatsRef.current.find((c) => c.id === chatId)
    if (chat?.invoice) URL.revokeObjectURL(chat.invoice.url)
    dispatch({ type: 'remove', chatId })
  }, [])

  return {
    chats: state.chats,
    active,
    busy,
    sendInvoice,
    sendQuestion,
    newChat: useCallback(() => dispatch({ type: 'newChat' }), []),
    selectChat: useCallback((chatId: string) => dispatch({ type: 'select', chatId }), []),
    removeChat,
  }
}
