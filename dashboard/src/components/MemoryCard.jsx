import React from 'react'

export default function MemoryCard({ memory, score, onDelete }) {
  if (!memory) return null

  const typeColors = {
    episodic: { bg: 'bg-synapse-500/10', text: 'text-synapse-300', dot: 'bg-synapse-500' },
    semantic: { bg: 'bg-green-500/10', text: 'text-green-300', dot: 'bg-green-500' },
    procedural: { bg: 'bg-yellow-500/10', text: 'text-yellow-300', dot: 'bg-yellow-500' },
  }

  const tc = typeColors[memory.memory_type] || typeColors.episodic

  const date = memory.created_at
    ? new Date(memory.created_at).toLocaleDateString('en-US', {
        month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
      })
    : ''

  return (
    <div className="bg-dark-800 rounded-xl border border-dark-500 p-4
                    hover:border-dark-300 transition-all group relative overflow-hidden">
      {/* Importance bar on top */}
      <div className="absolute top-0 left-0 right-0 h-0.5">
        <div
          className="h-full rounded-full"
          style={{
            width: `${(memory.importance_score || 0.5) * 100}%`,
            background: `linear-gradient(90deg, #4c6ef5, ${memory.importance_score > 0.7 ? '#40c057' : '#f59f00'})`
          }}
        />
      </div>

      <div className="flex items-start justify-between gap-3 mt-1">
        <div className="flex items-center gap-2 min-w-0">
          <span className={`w-2 h-2 rounded-full ${tc.dot} shrink-0`} />
          <span className={`text-xs font-medium ${tc.text}`}>
            {memory.memory_type}
          </span>
          {score !== undefined && (
            <span className="text-xs text-dark-400">
              {(score * 100).toFixed(0)}%
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-dark-400">{date}</span>
          {onDelete && (
            <button
              onClick={() => onDelete(memory.id)}
              className="opacity-0 group-hover:opacity-100 text-dark-400 hover:text-red-400 transition-all text-xs"
            >
              ✕
            </button>
          )}
        </div>
      </div>

      <p className="text-sm text-dark-50 mt-2 line-clamp-3">{memory.content}</p>

      {/* Tags */}
      {memory.tags && memory.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-3">
          {memory.tags.map((tag, i) => (
            <span key={i} className="text-xs px-1.5 py-0.5 rounded bg-dark-600 text-dark-200">
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* Importance bar label */}
      <div className="flex items-center gap-1 mt-2">
        <div className="flex-1 h-1 rounded-full bg-dark-600 overflow-hidden">
          <div
            className="h-full rounded-full bg-gradient-to-r from-synapse-500 to-purple-500"
            style={{ width: `${(memory.importance_score || 0.5) * 100}%` }}
          />
        </div>
        <span className="text-[10px] text-dark-400">
          {(memory.importance_score || 0).toFixed(2)}
        </span>
      </div>
    </div>
  )
}