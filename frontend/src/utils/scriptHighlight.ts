// Resaltado de guiones para el editor: convierte el texto plano (con las
// etiquetas <|emotion:*|>, <|prosody:*|>, <|sfx:*|> que consume el TTS) en
// tokens que el editor pinta como chips de color. El texto subyacente nunca
// cambia: lo que se guarda sigue siendo texto plano.

export type TagKind = 'emotion' | 'prosody' | 'sfx'

export interface ScriptToken {
  type: 'text' | 'tag'
  value: string
  tagKind?: TagKind
  tagName?: string
}

const TAG_RE = /<\|(emotion|prosody|sfx):([^|]+)\|>/g

export const TAG_COLORS: Record<TagKind, { chip: string; label: string }> = {
  emotion: { chip: 'bg-violet-500/25 text-violet-200 border-violet-400/40', label: 'emoción' },
  prosody: { chip: 'bg-cyan-500/20 text-cyan-200 border-cyan-400/40', label: 'prosodia' },
  sfx: { chip: 'bg-amber-500/20 text-amber-200 border-amber-400/40', label: 'sfx' },
}

export const SCRIPT_TAGS = [
  '<|emotion:contemplation|>',
  '<|emotion:sadness|>',
  '<|emotion:determination|>',
  '<|emotion:bitterness|>',
  '<|emotion:fear|>',
  '<|emotion:helplessness|>',
  '<|emotion:affection|>',
  '<|prosody:pause|>',
  '<|sfx:sigh|>',
  '<|sfx:laughter|>',
]

export function tokenizeScript(text: string): ScriptToken[] {
  const tokens: ScriptToken[] = []
  let last = 0
  for (const m of text.matchAll(TAG_RE)) {
    const idx = m.index
    if (idx > last) tokens.push({ type: 'text', value: text.slice(last, idx) })
    tokens.push({
      type: 'tag',
      value: m[0],
      tagKind: m[1] as TagKind,
      tagName: m[2].trim(),
    })
    last = idx + m[0].length
  }
  if (last < text.length) tokens.push({ type: 'text', value: text.slice(last) })
  return tokens
}

export function countWords(text: string): number {
  return text.trim() ? text.trim().split(/\s+/).length : 0
}

/** Duración estimada de narración en minutos (~140 palabras/min en español). */
export function estimateMinutes(text: string, wpm = 140): number {
  return Math.round(countWords(text) / wpm)
}

/** Divide un token de texto en sub-tokens resaltando las coincidencias de búsqueda. */
export function splitByQuery(
  token: ScriptToken,
  query: string
): { value: string; match: boolean }[] {
  if (!query) return [{ value: token.value, match: false }]
  const lower = token.value.toLowerCase()
  const q = query.toLowerCase()
  const parts: { value: string; match: boolean }[] = []
  let i = 0
  while (i <= lower.length) {
    const found = lower.indexOf(q, i)
    if (found === -1) {
      parts.push({ value: token.value.slice(i), match: false })
      break
    }
    if (found > i) parts.push({ value: token.value.slice(i, found), match: false })
    parts.push({ value: token.value.slice(found, found + q.length), match: true })
    i = found + q.length
  }
  return parts.filter((p) => p.value.length > 0)
}
