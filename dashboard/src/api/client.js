import axios from 'axios'

const client = axios.create({
  baseURL: '/api',
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
})

export async function getHealth() {
  const { data } = await client.get('/health')
  return data
}

export async function getStats() {
  const { data } = await client.get('/memory/stats')
  return data
}

export async function storeMemory(content, source = '', tags = []) {
  const { data } = await client.post('/memory', { content, source, tags })
  return data
}

export async function retrieveMemories(query, topK = 20) {
  const { data } = await client.get('/memory/retrieve', {
    params: { query, top_k: topK },
  })
  return data
}

export async function reflect(topic, topK = 15) {
  const { data } = await client.get('/memory/reflect', {
    params: { topic, top_k: topK },
  })
  return data
}

export async function consolidate() {
  const { data } = await client.post('/memory/consolidate')
  return data
}

export async function forgetMemories(threshold = 0.1) {
  const { data } = await client.post('/memory/forget', { threshold })
  return data
}

export async function deleteMemory(id) {
  const { data } = await client.delete(`/memory/${id}`)
  return data
}