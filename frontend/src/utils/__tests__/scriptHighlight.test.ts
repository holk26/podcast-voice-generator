import { describe, it, expect } from 'vitest'
import {
  tokenizeScript,
  countWords,
  estimateMinutes,
  splitByQuery,
  SCRIPT_TAGS,
} from '../scriptHighlight'

describe('tokenizeScript', () => {
  it('devuelve texto plano como un solo token', () => {
    expect(tokenizeScript('Hola mundo')).toEqual([{ type: 'text', value: 'Hola mundo' }])
  })

  it('detecta etiquetas de emoción, prosodia y sfx', () => {
    const tokens = tokenizeScript('<|emotion:fear|> Cuidado <|prosody:pause|> <|sfx:sigh|>')
    const tags = tokens.filter((t) => t.type === 'tag')
    expect(tags).toHaveLength(3)
    expect(tags[0]).toMatchObject({ tagKind: 'emotion', tagName: 'fear' })
    expect(tags[1]).toMatchObject({ tagKind: 'prosody', tagName: 'pause' })
    expect(tags[2]).toMatchObject({ tagKind: 'sfx', tagName: 'sigh' })
    // El texto entre etiquetas se conserva tal cual
    expect(tokens.map((t) => t.value).join('')).toBe('<|emotion:fear|> Cuidado <|prosody:pause|> <|sfx:sigh|>')
  })

  it('no confunde corchetes sueltos con etiquetas', () => {
    const tokens = tokenizeScript('usa <pipe> y |separadores|')
    expect(tokens.every((t) => t.type === 'text')).toBe(true)
  })
})

describe('countWords / estimateMinutes', () => {
  it('cuenta palabras ignorando espacios extra', () => {
    expect(countWords('  uno dos   tres ')).toBe(3)
    expect(countWords('')).toBe(0)
    expect(countWords('   ')).toBe(0)
  })

  it('estima minutos a ~140 palabras por minuto', () => {
    const text = Array(280).fill('palabra').join(' ')
    expect(estimateMinutes(text)).toBe(2)
  })
})

describe('splitByQuery', () => {
  it('resalta coincidencias case-insensitive', () => {
    const token = { type: 'text' as const, value: 'El Caso del Caso' }
    const parts = splitByQuery(token, 'caso')
    expect(parts).toEqual([
      { value: 'El ', match: false },
      { value: 'Caso', match: true },
      { value: ' del ', match: false },
      { value: 'Caso', match: true },
    ])
  })

  it('sin query devuelve el token completo sin marcar', () => {
    const token = { type: 'text' as const, value: 'hola' }
    expect(splitByQuery(token, '')).toEqual([{ value: 'hola', match: false }])
  })
})

describe('SCRIPT_TAGS', () => {
  it('todas las etiquetas del botonero tienen formato válido', () => {
    for (const tag of SCRIPT_TAGS) {
      expect(tag).toMatch(/^<\|(emotion|prosody|sfx):[a-z_]+\|>$/)
    }
  })
})
