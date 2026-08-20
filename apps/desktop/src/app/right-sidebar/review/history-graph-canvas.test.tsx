import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { CommitGraphCell, getLaneColor } from './history-graph-canvas'

describe('CommitGraphCell', () => {
  it('renders a linear commit node and lines', () => {
    const row = { branchIn: [], lane: 0, through: [0] }
    const { container } = render(<CommitGraphCell maxLane={0} row={row} />)

    const svg = container.querySelector('svg')
    expect(svg).not.toBeNull()

    const circles = container.querySelectorAll('circle')
    // Normal node has 2 circles (outer stroke + inner dot)
    expect(circles.length).toBe(2)

    const lines = container.querySelectorAll('line')
    // 1 through line + top line + bottom line = 3
    expect(lines.length).toBe(3)
  })

  it('renders branch-in merge curve when second parent exists', () => {
    const row = { branchIn: [1], lane: 0, through: [0, 1] }
    const { container } = render(<CommitGraphCell maxLane={1} row={row} />)

    const path = container.querySelector('path')
    expect(path).not.toBeNull()
    expect(path?.getAttribute('d')).toContain('M')
    expect(path?.getAttribute('d')).toContain('C')
  })

  it('renders halo circle when selected', () => {
    const row = { branchIn: [], lane: 0, through: [] }
    const { container } = render(<CommitGraphCell maxLane={0} row={row} selected />)

    const circles = container.querySelectorAll('circle')
    // Selected node has 3 circles (selection halo + outer stroke + inner dot)
    expect(circles.length).toBe(3)
  })

  it('provides distinct lane colors', () => {
    const color0 = getLaneColor(0)
    const color1 = getLaneColor(1)
    expect(color0).not.toBe(color1)
    expect(color0).toMatch(/^#[0-9A-Fa-f]{6}$/)
  })
})
