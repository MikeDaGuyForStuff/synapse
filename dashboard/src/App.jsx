import React, { useState, useEffect, useCallback } from 'react'
import MemoryGraph from './components/MemoryGraph'
import Timeline from './components/Timeline'
import SearchBar from './components/SearchBar'
import MemoryCard from './components/MemoryCard'
import StatsPanel from './components/StatsPanel'
import * as api from './api/client'

export default function App() {
  const [memories, setMemories] = useState([])
  const [stats, setStats] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [reflectResult, setReflectResult] = useState(null)
  const [activeTab, setActiveTab] = useState('graph')

  const loadInitial = useCallback(async () => {
    try {
      const s = await api.getStats()
      setStats(s)
      if (s.total_memories > 0) {
        const m = await api.retrieveMemories('', 50)
        setMemories(m)
      }
    } catch (e) {
      console.error('Failed to load:', e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadInitial() }, [loadInitial])

  const handleSearch = async (query) => {
    setSearchQuery(query)
    if (!query.trim()) {
      loadInitial()
      return
    }
    setLoading(true)
    try {
      const results = await api.retrieveMemories(query, 30)
      setMemories(results)
      const ref = await api.reflect(query)
      setReflectResult(ref)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const handleStore = async (content, tags) => {
    try {
      await api.storeMemory(content, 'dashboard', tags.split(',').map(t => t.trim()).filter(Boolean))
      await loadInitial()
    } catch (e) {
      console.error(e)
    }
  }

  const handleDelete = async (id) => {
    try {
      await api.deleteMemory(id)
      setMemories(prev => prev.filter(m => m.memory?.id !== id))
    } catch (e) {
      console.error(e)
    }
  }

  const handleConsolidate = async () => {
    try {
      const result = await api.consolidate()
      await loadInitial()
      return result
    } catch (e) {
      console.error(e)
    }
  }

  return (
    <div className="min-h-screen bg-dark-900 text-dark-50">
      {/* Header */}
      <header className="border-b border-dark-500 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-synapse-500 to-purple-500 flex items-center justify-center text-xs font-bold">
              S
            </div>
            <h1 className="text-xl font-bold tracking-tight">SYNAPSE</h1>
            <span className="text-dark-200 text-sm ml-2">Memory Engine</span>
          </div>
          {stats && <StatsPanel stats={stats} />}
        </div>
      </header>

      {/* Search */}
      <div className="border-b border-dark-500 px-6 py-3">
        <div className="max-w-7xl mx-auto">
          <SearchBar onSearch={handleSearch} onStore={handleStore} />
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-dark-500 px-6">
        <div className="max-w-7xl mx-auto flex gap-6">
          {[
            { id: 'graph', label: 'Memory Graph', icon: '○' },
            { id: 'timeline', label: 'Timeline', icon: '≡' },
            { id: 'cards', label: 'Cards', icon: '▦' },
            { id: 'reflect', label: 'Reflect', icon: '◎' },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`py-3 px-2 border-b-2 text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? 'border-synapse-500 text-synapse-300'
                  : 'border-transparent text-dark-200 hover:text-dark-50'
              }`}
            >
              {tab.icon} {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto p-6">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="text-dark-200 synapse-pulse text-lg">Loading memories...</div>
          </div>
        ) : (
          <>
            {/* Tab: Graph */}
            {activeTab === 'graph' && (
              <div className="h-[600px] bg-dark-800 rounded-xl border border-dark-500 overflow-hidden">
                <MemoryGraph
                  memories={memories}
                  onNodeClick={(mem) => {
                    setSearchQuery(mem.content.substring(0, 40))
                  }}
                />
              </div>
            )}

            {/* Tab: Timeline */}
            {activeTab === 'timeline' && (
              <Timeline
                memories={memories}
                onDelete={handleDelete}
                onConsolidate={handleConsolidate}
              />
            )}

            {/* Tab: Cards */}
            {activeTab === 'cards' && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {memories.length === 0 && (
                  <div className="col-span-full text-center text-dark-200 py-20">
                    No memories yet. Store something above.
                  </div>
                )}
                {memories.map((item, i) => (
                  <MemoryCard
                    key={item.memory?.id || i}
                    memory={item.memory || item}
                    score={item.combined_score}
                    onDelete={handleDelete}
                  />
                ))}
              </div>
            )}

            {/* Tab: Reflect */}
            {activeTab === 'reflect' && (
              <div className="space-y-6">
                {reflectResult ? (
                  <>
                    <div className="bg-dark-800 rounded-xl border border-dark-500 p-6">
                      <h2 className="text-lg font-semibold mb-2">Reflection</h2>
                      <p className="text-dark-100">{reflectResult.summary}</p>
                    </div>
                    {reflectResult.context_block && (
                      <div className="bg-dark-800 rounded-xl border border-dark-500 p-6">
                        <h2 className="text-lg font-semibold mb-2">Context Block</h2>
                        <pre className="text-sm text-dark-100 whitespace-pre-wrap font-mono bg-dark-900 p-4 rounded-lg">
                          {reflectResult.context_block}
                        </pre>
                      </div>
                    )}
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {reflectResult.memories?.map((mem) => (
                        <MemoryCard key={mem.id} memory={mem} />
                      ))}
                    </div>
                  </>
                ) : (
                  <div className="text-center text-dark-200 py-20">
                    Search for something above to see a reflection.
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </main>
    </div>
  )
}