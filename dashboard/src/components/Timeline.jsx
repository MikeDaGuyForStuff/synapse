import React, { useState } from 'react'

export default function Timeline({ memories, onDelete, onConsolidate }) {
  const [consolidating, setConsolidating] = useState(false)

  const handleConsolidate = async () => {
    setConsolidating(true)
    await onConsolidate()
    setConsolidating(false)
  }

  // Sort by created_at descending
  const sorted = [...memories]
    .sort((a, b) => {
      const da = a.memory?.created_at || a.created_at || ''
      const db = b.memory?.created_at || b.created_at || ''
      return db.localeCompare(da)
    })

  const typeColors = {
    episodic: 'bg-synapse-500',
    semantic: 'bg-green-500',
    procedural: 'bg-yellow-500',
  }

  return (
    <div className="space-y-6">
      {/* Controls */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">
          {sorted.length} memories
        </h2>
        <button
          onClick={handleConsolidate}
          disabled={consolidating}
          className="px-3 py-1.5 bg-synapse-600 hover:bg-synapse-700 disabled:opacity-50
                     rounded-lg text-sm font-medium transition-colors"
        >
          {consolidating ? 'Consolidating...' : 'Consolidate'}
        </button>
      </div>

      {/* Timeline */}
      {sorted.length === 0 && (
        <div className="text-center text-dark-200 py-20">
          No memories in the timeline.
        </div>
      )}

      <div className="relative">
        {/* Center line */}
        <div className="absolute left-8 top-0 bottom-0 w-0.5 bg-dark-500" />

        <div className="space-y-4">
          {sorted.map((item, i) => {
            const mem = item.memory || item
            const date = mem.created_at
              ? new Date(mem.created_at).toLocaleDateString('en-US', {
                  month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
                })
              : 'unknown'

            return (
              <div key={mem.id || i} className="relative pl-20 group">
                {/* Dot on timeline */}
                <div className={`absolute left-5 top-3 w-6 h-6 rounded-full border-2 border-dark-700
                  ${typeColors[mem.memory_type] || 'bg-synapse-500'} flex items-center justify-center`}>
                  <div className="w-2 h-2 rounded-full bg-white opacity-80" />
                </div>

                {/* Card */}
                <div className="bg-dark-800 rounded-lg border border-dark-500 p-4
                                hover:border-dark-300 transition-colors">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-dark-50">{mem.content}</p>
                      <div className="flex items-center gap-2 mt-2">
                        <span className={`text-xs px-1.5 py-0.5 rounded ${
                          mem.memory_type === 'episodic' ? 'bg-synapse-500/20 text-synapse-300' :
                          mem.memory_type === 'semantic' ? 'bg-green-500/20 text-green-300' :
                          'bg-yellow-500/20 text-yellow-300'
                        }`}>
                          {mem.memory_type}
                        </span>
                        <span className="text-xs text-dark-200">
                          importance: {mem.importance_score?.toFixed(2)}
                        </span>
                        <span className="text-xs text-dark-300">{date}</span>
                      </div>
                    </div>
                    {onDelete && (
                      <button
                        onClick={() => onDelete(mem.id)}
                        className="opacity-0 group-hover:opacity-100 text-dark-300
                                   hover:text-red-400 transition-all shrink-0"
                        title="Delete"
                      >
                        ✕
                      </button>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}