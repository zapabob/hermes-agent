import { useMemo } from 'react'

import type { CommitGraphRow } from './history-graph'

// Lane colors tailored for dark/light themes (vibrant, high contrast)
const LANE_COLORS = [
  '#00D8FF', // Cyan
  '#FFD700', // Gold
  '#FF69B4', // Hot Pink
  '#00FF7F', // Spring Green
  '#BA55D3', // Medium Orchid
  '#FF8C00', // Dark Orange
  '#38BDF8', // Sky Blue
  '#A855F7', // Purple
  '#EC4899', // Pink
  '#10B981'  // Emerald
]

export function getLaneColor(lane: number): string {
  return LANE_COLORS[lane % LANE_COLORS.length]
}

interface CommitGraphCellProps {
  row: CommitGraphRow
  selected?: boolean
  laneWidth?: number
  height?: number
  maxLane: number
}

/**
 * Render an individual commit's graph cell (SVG nodes, through lines, branching & merge curves).
 * Perfectly aligns with the commit list item row height.
 */
export function CommitGraphCell({
  row,
  selected = false,
  laneWidth = 14,
  height = 42,
  maxLane
}: CommitGraphCellProps) {
  const totalWidth = Math.max(1, maxLane + 1) * laneWidth + 8
  const cy = height / 2
  const nodeX = row.lane * laneWidth + 10

  // Path coordinates
  const throughLines = useMemo(() => {
    return row.through.map(lane => {
      const x = lane * laneWidth + 10
      return { lane, x }
    })
  }, [row.through, laneWidth])

  const branchInCurves = useMemo(() => {
    return row.branchIn.map(parentLane => {
      const parentX = parentLane * laneWidth + 10
      // Draw bezier curve from child node (nodeX, cy) to parent lane bottom (parentX, height)
      const d = `M ${nodeX} ${cy} C ${nodeX} ${cy + (height - cy) * 0.6}, ${parentX} ${cy + (height - cy) * 0.4}, ${parentX} ${height}`
      return { d, parentLane }
    })
  }, [row.branchIn, nodeX, cy, height, laneWidth])

  return (
    <svg
      aria-hidden="true"
      className="shrink-0 overflow-visible"
      height={height}
      style={{ width: `${totalWidth}px` }}
      width={totalWidth}
    >
      {/* 1. Through vertical lines (lanes passing through this commit from above to below) */}
      {throughLines.map(({ lane, x }) => (
        <line
          key={`through-${lane}`}
          stroke={getLaneColor(lane)}
          strokeOpacity={0.7}
          strokeWidth={1.75}
          x1={x}
          x2={x}
          y1={0}
          y2={height}
        />
      ))}

      {/* 2. Top half line connecting from previous commit in this lane to current node */}
      <line
        stroke={getLaneColor(row.lane)}
        strokeWidth={1.75}
        x1={nodeX}
        x2={nodeX}
        y1={0}
        y2={cy}
      />

      {/* 3. Bottom half line if this lane continues down */}
      <line
        stroke={getLaneColor(row.lane)}
        strokeWidth={1.75}
        x1={nodeX}
        x2={nodeX}
        y1={cy}
        y2={height}
      />

      {/* 4. Branch-in / Merge curves */}
      {branchInCurves.map(({ d, parentLane }) => (
        <path
          d={d}
          fill="none"
          key={`branch-${parentLane}`}
          stroke={getLaneColor(parentLane)}
          strokeOpacity={0.85}
          strokeWidth={1.75}
        />
      ))}

      {/* 5. Commit Node (circle) */}
      {selected ? (
        <circle
          cx={nodeX}
          cy={cy}
          fill={getLaneColor(row.lane)}
          fillOpacity={0.3}
          r={7}
        />
      ) : null}
      <circle
        cx={nodeX}
        cy={cy}
        fill="var(--ui-bg-primary, #120824)"
        r={4.5}
        stroke={getLaneColor(row.lane)}
        strokeWidth={2}
      />
      <circle
        cx={nodeX}
        cy={cy}
        fill={getLaneColor(row.lane)}
        r={2.5}
      />
    </svg>
  )
}
