import React, { useState } from 'react'

export default function SearchBar({ onSearch, onStore }) {
  const [query, setQuery] = useState('')
  const [showStore, setShowStore] = useState(false)
  const [storeContent, setStoreContent] = useState('')
  const [storeTags, setStoreTags] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    onSearch(query)
  }

  const handleStore = (e) => {
    e.preventDefault()
    if (!storeContent.trim()) return
    onStore(storeContent, storeTags)
    setStoreContent('')
    setStoreTags('')
    setShowStore(false)
  }

  return (
    <div className="flex gap-3">
      <form onSubmit={handleSubmit} className="flex-1 flex gap-3">
        <div className="relative flex-1">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search memories..."
            className="w-full bg-dark-700 border border-dark-400 rounded-lg px-4 py-2
                       text-dark-50 placeholder-dark-300 focus:outline-none focus:border-synapse-500
                       text-sm transition-colors"
          />
        </div>
        <button
          type="submit"
          className="px-4 py-2 bg-synapse-600 hover:bg-synapse-700 rounded-lg text-sm
                     font-medium transition-colors"
        >
          Search
        </button>
      </form>
      <button
        onClick={() => setShowStore(!showStore)}
        className="px-4 py-2 border border-dark-400 hover:border-dark-200 rounded-lg text-sm
                   font-medium transition-colors"
      >
        + Store
      </button>
      {showStore && (
        <form onSubmit={handleStore} className="flex gap-3 items-start">
          <input
            type="text"
            value={storeContent}
            onChange={(e) => setStoreContent(e.target.value)}
            placeholder="Memory content..."
            className="w-80 bg-dark-700 border border-dark-400 rounded-lg px-4 py-2
                       text-dark-50 placeholder-dark-300 focus:outline-none focus:border-synapse-500
                       text-sm transition-colors"
            autoFocus
          />
          <input
            type="text"
            value={storeTags}
            onChange={(e) => setStoreTags(e.target.value)}
            placeholder="tags (comma separated)"
            className="w-48 bg-dark-700 border border-dark-400 rounded-lg px-4 py-2
                       text-dark-50 placeholder-dark-300 focus:outline-none focus:border-synapse-500
                       text-sm transition-colors"
          />
          <button type="submit" className="px-3 py-2 bg-green-600 hover:bg-green-700 rounded-lg text-sm font-medium transition-colors">
            Save
          </button>
        </form>
      )}
    </div>
  )
}