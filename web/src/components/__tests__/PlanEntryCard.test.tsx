import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import PlanEntryCard from '../PlanEntryCard'
import type { ContentPlanEntry } from '../../types'

const entry: ContentPlanEntry = {
  id: 1,
  channel_id: 1,
  title: 'E1',
  description: 'Desc',
  status: 'draft',
  created_at: '',
  updated_at: '',
}

describe('PlanEntryCard', () => {
  it('calls approve on click', () => {
    const onApprove = vi.fn()
    render(<PlanEntryCard entry={entry} onApprove={onApprove} onReject={vi.fn()} onDelete={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: /Aprobar/i }))
    expect(onApprove).toHaveBeenCalledWith(1)
  })
})
