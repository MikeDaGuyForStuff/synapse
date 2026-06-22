import React from 'react'

export default function StatsPanel({ stats }) {
  if (!stats) return null

  return (
    <div className="flex items-center gap-6 text-sm">
      <div className="flex items-center gap-2">
        <div className="w-2 h-2 rounded-full bg-synapse-500" />
        <span className="text-dark-200">Total</span>
        <span className="font-semibold">{stats.total_memories}</span>
      </div>
      {stats.type_breakdown && (
        <>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-synapse-500" />
            <span className="text-dark-300 text-xs">E</span>
            <span className="text-dark-200">{stats.type_breakdown.episodic || 0}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-green-500" />
            <span className="text-dark-300 text-xs">S</span>
            <span className="text-dark-200">{stats.type_breakdown.semantic || 0}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-yellow-500" />
            <span className="text-dark-300 text-xs">P</span>
            <span className="text-dark-200">{stats.type_breakdown.procedural || 0}</span>
          </div>
        </>
      )}
      {stats.avg_importance !== undefined && (
        <div className="flex items-center gap-2">
          <span className="text-dark-300">μ</span>
          <span className="text-dark-200">{stats.avg_importance.toFixed(2)}</span>
        </div>
      )}
    </div>
  )
}