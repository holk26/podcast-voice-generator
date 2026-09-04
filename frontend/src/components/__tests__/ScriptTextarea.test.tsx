import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import ScriptTextarea from '../ScriptTextarea'

describe('ScriptTextarea', () => {
  it('renderiza el texto y pinta las etiquetas como chips', () => {
    const { container } = render(
      <ScriptTextarea
        value="<|emotion:fear|> Una noche oscura."
        onChange={() => {}}
      />
    )
    // El textarea real conserva el valor exacto (texto plano)
    expect(screen.getByTestId('script-textarea')).toHaveValue('<|emotion:fear|> Una noche oscura.')
    // La capa de resaltado (pre) muestra el chip legible
    const overlay = container.querySelector('pre[aria-hidden]') as HTMLPreElement
    expect(overlay.textContent).toContain('emotion:fear')
    expect(overlay.textContent).toContain('Una noche oscura.')
  })

  it('propaga los cambios al escribir', () => {
    const onChange = vi.fn()
    render(<ScriptTextarea value="" onChange={onChange} />)
    fireEvent.change(screen.getByTestId('script-textarea'), { target: { value: 'Hola' } })
    expect(onChange).toHaveBeenCalledWith('Hola')
  })

  it('el botón de etiqueta inserta el tag en el cursor', () => {
    const onChange = vi.fn()
    render(<ScriptTextarea value="Hola mundo" onChange={onChange} />)
    const ta = screen.getByTestId('script-textarea') as HTMLTextAreaElement
    ta.focus()
    ta.setSelectionRange(5, 5)
    fireEvent.click(screen.getByTitle('<|emotion:fear|>'))
    expect(onChange).toHaveBeenCalledWith('Hola <|emotion:fear|> mundo')
  })

  it('buscar cuenta coincidencias y navega', () => {
    render(<ScriptTextarea value="caso abierto, caso cerrado" onChange={() => {}} />)
    fireEvent.click(screen.getByText('🔍 Buscar'))
    fireEvent.change(screen.getByPlaceholderText('Buscar…'), { target: { value: 'caso' } })
    expect(screen.getByTestId('match-count')).toHaveTextContent('2 coincidencias')
  })

  it('reemplazar todo sustituye todas las coincidencias', () => {
    const onChange = vi.fn()
    render(<ScriptTextarea value="caso abierto, caso cerrado" onChange={onChange} />)
    fireEvent.click(screen.getByText('🔍 Buscar'))
    fireEvent.change(screen.getByPlaceholderText('Buscar…'), { target: { value: 'caso' } })
    fireEvent.change(screen.getByPlaceholderText('Reemplazar por…'), { target: { value: 'proceso' } })
    fireEvent.click(screen.getByText('Reemplazar todo'))
    expect(onChange).toHaveBeenCalledWith('proceso abierto, proceso cerrado')
  })
})
