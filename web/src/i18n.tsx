import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'

export type Lang = 'fr' | 'en'
export const LANGS: Lang[] = ['fr', 'en']

const fr = {
  langName: 'Français',
  tagline: 'Saisie de factures',
  newChat: 'Nouvelle discussion',
  history: 'Discussions de cette session',
  historyEmpty: 'Vos factures lues apparaîtront ici.',
  historyNote: 'L’historique reste dans cet onglet seulement : il disparaît si vous actualisez la page. Rien n’est enregistré sur le serveur.',
  untitled: (name: string) => name || 'Facture',
  noInvoiceChat: 'Sans facture',
  readingShort: 'Lecture…',
  deleteChat: (title: string) => `Supprimer « ${title} »`,
  openHistory: 'Ouvrir l’historique',
  closeHistory: 'Fermer l’historique',
  railNote: 'Lecture par un modèle image + texte entraîné pour ce projet. Les exemples sont des factures générées.',
  headline: ['Envoyez une facture.', 'Je la prépare pour la saisie.'],
  intro:
    'Fournisseur, NIF, RC, date, lignes, HT, TVA et TTC sont relevés depuis la photo, puis les totaux sont recalculés. Ensuite, posez vos questions sur la facture, en français ou en anglais.',
  samplesPrompt: 'Pas de facture sous la main ? Prenez-en une :',
  sampleName: (n: number) => `Exemple ${n}`,
  sampleAria: (n: number) => `Utiliser l’exemple ${n}`,
  attach: 'Joindre une facture',
  attachOther: 'Autre facture',
  attachShort: 'Joindre',
  fileLabel: 'Fichier de la facture',
  questionLabel: 'Question',
  placeholderAsk: 'Une question sur la facture ?',
  placeholderStart: 'Joignez une facture pour commencer',
  send: 'Envoyer la question',
  hint: 'JPEG ou PNG, 6 Mo maximum. Vous pouvez aussi déposer l’image n’importe où sur la page.',
  dropHere: 'Déposez la facture ici',
  you: 'Vous',
  sentInvoice: (name: string) => `Facture envoyée : ${name}`,
  reading: 'Lecture de la facture',
  searching: 'Recherche sur la facture',
  introVerified: 'Voici la fiche de saisie. Les totaux se recalculent correctement.',
  introReview: (n: number) =>
    `Voici la fiche de saisie. ${n === 1 ? 'Un contrôle ne passe pas' : `${n} contrôles ne passent pas`} : relisez la ligne en rouge avant de saisir.`,
  introUnknown: 'Voici ce que j’ai relevé. Il manque des montants pour contrôler les totaux.',
  askPrompt: 'À demander :',
  suggestions: ['Quel est le montant TTC ?', 'Quel est le NIF du fournisseur ?', 'Qui est le client ?'],
  notFound: 'Cette information n’apparaît pas sur la facture.',
  notes: {
    notImage: 'Ce fichier n’est pas une image JPEG ou PNG. Joignez une photo ou un scan de la facture.',
    tooBig: 'L’image dépasse 6 Mo. Envoyez une photo plus légère.',
    needInvoice: 'Joignez d’abord une facture : mes réponses portent sur l’image envoyée.',
    offline: 'Le serveur ne répond pas. Vérifiez qu’il est démarré, puis réessayez.',
    unexpected: 'Réponse inattendue du serveur.',
    status: (code: number) => `Le serveur a répondu ${code}.`,
    rateLimited: (s: number) => `Trop de demandes d’affilée. Réessayez dans ${s} secondes.`,
  },
  toReview: 'À vérifier',
  slip: {
    label: 'Fiche de saisie',
    vendor: 'Fournisseur',
    client: 'Client',
    notRead: 'non lu',
    invoiceNumber: 'N° de facture',
    date: 'Date',
    item: 'Désignation',
    qty: 'Qté',
    unitPrice: 'P.U. HT',
    amount: 'Montant HT',
    totalHt: 'Total HT',
    tva: 'TVA',
    timbre: 'Droit de timbre',
    totalTtc: 'Total TTC',
    checks: 'Contrôles',
    showJson: 'Voir le JSON à importer',
    hideJson: 'Masquer le JSON',
    readIn: (s: string) => `Lu en ${s} s`,
    ok: 'vérifié',
    bad: 'à vérifier',
  },
  stamp: { verified: 'Vérifié', review: 'À vérifier', verifiedSub: 'Totaux justes', reviewSub: 'Totaux à revoir', verifiedSr: 'Totaux vérifiés', reviewSr: 'À vérifier avant saisie' },
  checks: {
    total: 'HT + TVA + timbre = TTC',
    lines: 'Somme des lignes = HT',
    nif: 'NIF à 15 chiffres',
    date: 'Date valide',
    tva: (rate: string) => `TVA = ${rate} du HT`,
    detail: (want: string, got: string) => `attendu ${want}, lu ${got}`,
  },
}

export type Messages = typeof fr

const en: Messages = {
  langName: 'English',
  tagline: 'Supplier invoice entry',
  newChat: 'New chat',
  history: 'Chats in this session',
  historyEmpty: 'The invoices you read will show here.',
  historyNote: 'History stays in this tab only: refreshing the page clears it. Nothing is saved on the server.',
  untitled: (name) => name || 'Invoice',
  noInvoiceChat: 'No invoice',
  readingShort: 'Reading…',
  deleteChat: (title) => `Delete “${title}”`,
  openHistory: 'Open history',
  closeHistory: 'Close history',
  railNote: 'Read by an image + text model trained for this project. The samples are generated invoices.',
  headline: ['Send an invoice.', 'I get it ready for entry.'],
  intro:
    'Supplier, tax ID (NIF), trade register (RC), date, lines, net total, VAT and gross total are read from the photo, then the totals are recalculated. Then ask questions about the invoice, in English or French.',
  samplesPrompt: 'No invoice at hand? Take one:',
  sampleName: (n) => `Sample ${n}`,
  sampleAria: (n) => `Use sample ${n}`,
  attach: 'Attach an invoice',
  attachOther: 'Another invoice',
  attachShort: 'Attach',
  fileLabel: 'Invoice file',
  questionLabel: 'Question',
  placeholderAsk: 'Ask about the invoice',
  placeholderStart: 'Attach an invoice to start',
  send: 'Send the question',
  hint: 'JPEG or PNG, 6 MB maximum. You can also drop the image anywhere on the page.',
  dropHere: 'Drop the invoice here',
  you: 'You',
  sentInvoice: (name) => `Invoice sent: ${name}`,
  reading: 'Reading the invoice',
  searching: 'Looking on the invoice',
  introVerified: 'Here is the entry sheet. The totals add up.',
  introReview: (n) =>
    `Here is the entry sheet. ${n === 1 ? 'One check fails' : `${n} checks fail`}: read the red line again before entering it.`,
  introUnknown: 'Here is what I read. Some amounts are missing, so the totals cannot be checked.',
  askPrompt: 'Ask:',
  suggestions: ['What is the total amount to pay?', 'What is the supplier’s NIF?', 'Who is the customer?'],
  notFound: 'This information is not on the invoice.',
  notes: {
    notImage: 'This file is not a JPEG or PNG image. Attach a photo or a scan of the invoice.',
    tooBig: 'The image is over 6 MB. Send a lighter photo.',
    needInvoice: 'Attach an invoice first: my answers are about the image you send.',
    offline: 'The server is not responding. Check that it is running, then try again.',
    unexpected: 'Unexpected response from the server.',
    status: (code) => `The server answered ${code}.`,
    rateLimited: (s) => `Too many requests in a row. Try again in ${s} seconds.`,
  },
  toReview: 'To review',
  slip: {
    label: 'Entry sheet',
    vendor: 'Supplier',
    client: 'Customer',
    notRead: 'not read',
    invoiceNumber: 'Invoice no.',
    date: 'Date',
    item: 'Item',
    qty: 'Qty',
    unitPrice: 'Unit price',
    amount: 'Net amount',
    totalHt: 'Net total (HT)',
    tva: 'VAT',
    timbre: 'Stamp duty',
    totalTtc: 'Total (TTC)',
    checks: 'Checks',
    showJson: 'Show the JSON to import',
    hideJson: 'Hide the JSON',
    readIn: (s) => `Read in ${s} s`,
    ok: 'checked',
    bad: 'to review',
  },
  stamp: { verified: 'Verified', review: 'Review', verifiedSub: 'Totals correct', reviewSub: 'Totals off', verifiedSr: 'Totals verified', reviewSr: 'Review before entry' },
  checks: {
    total: 'Net + VAT + stamp duty = total',
    lines: 'Sum of lines = net total',
    nif: 'NIF has 15 digits',
    date: 'Valid date',
    tva: (rate) => `VAT = ${rate} of net total`,
    detail: (want, got) => `expected ${want}, read ${got}`,
  },
}

export const MESSAGES: Record<Lang, Messages> = { fr, en }

const STORAGE_KEY = 'invoicedesk.lang'

function initialLang(): Lang {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved === 'fr' || saved === 'en') return saved
  } catch {
    /* storage can be blocked; fall back to the browser language */
  }
  return typeof navigator !== 'undefined' && navigator.language.toLowerCase().startsWith('fr') ? 'fr' : 'en'
}

interface I18n {
  lang: Lang
  t: Messages
  setLang: (lang: Lang) => void
}

const Ctx = createContext<I18n | null>(null)

export function I18nProvider({ children, lang: fixed }: { children: ReactNode; lang?: Lang }) {
  const [lang, setLangState] = useState<Lang>(fixed ?? initialLang)
  const setLang = useCallback((l: Lang) => {
    setLangState(l)
    try {
      localStorage.setItem(STORAGE_KEY, l)
    } catch {
      /* not persisted */
    }
  }, [])
  useEffect(() => {
    document.documentElement.lang = lang
  }, [lang])
  const value = useMemo(() => ({ lang, t: MESSAGES[lang], setLang }), [lang, setLang])
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useI18n(): I18n {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('useI18n needs <I18nProvider>')
  return ctx
}
