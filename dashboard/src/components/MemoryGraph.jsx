import React, { useRef, useEffect } from 'react'
import * as d3 from 'd3'

export default function MemoryGraph({ memories, onNodeClick }) {
  const svgRef = useRef(null)

  useEffect(() => {
    if (!svgRef.current || !memories.length) return

    const svg = d3.select(svgRef.current)
    const width = svgRef.current.clientWidth
    const height = svgRef.current.clientHeight

    svg.selectAll('*').remove()

    // Build graph data
    const nodes = memories.map((item, i) => ({
      id: item.memory?.id || i,
      label: (item.memory?.content || item.content || '').substring(0, 40),
      type: item.memory?.memory_type || item.memory_type || 'episodic',
      importance: item.memory?.importance_score || item.importance_score || 0.5,
      score: item.combined_score || 0,
      data: item.memory || item,
    }))

    // Build links from linked_memories
    const nodeIds = new Set(nodes.map(n => n.id))
    const links = []
    nodes.forEach(n => {
      const linked = n.data.linked_memories || []
      linked.forEach(lid => {
        if (nodeIds.has(lid)) {
          links.push({ source: n.id, target: lid })
        }
      })
    })

    // If no links, create some based on similarity
    if (links.length === 0 && nodes.length > 1) {
      for (let i = 1; i < nodes.length; i++) {
        links.push({ source: nodes[i-1].id, target: nodes[i].id })
      }
    }

    // Color by type
    const typeColors = {
      episodic: '#4c6ef5',
      semantic: '#40c057',
      procedural: '#f59f00',
    }

    const simulation = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(links).id(d => d.id).distance(120))
      .force('charge', d3.forceManyBody().strength(-200))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide(40))

    // Container
    const g = svg.append('g')

    // Zoom
    svg.call(d3.zoom()
      .scaleExtent([0.2, 4])
      .on('zoom', (event) => g.attr('transform', event.transform))
    )

    // Links
    const link = g.append('g')
      .selectAll('line')
      .data(links)
      .join('line')
      .attr('stroke', '#373A40')
      .attr('stroke-width', 1.5)
      .attr('stroke-opacity', 0.6)

    // Node groups
    const node = g.append('g')
      .selectAll('g')
      .data(nodes)
      .join('g')
      .style('cursor', 'pointer')
      .call(d3.drag()
        .on('start', (event, d) => {
          if (!event.active) simulation.alphaTarget(0.3).restart()
          d.fx = d.x
          d.fy = d.y
        })
        .on('drag', (event, d) => {
          d.fx = event.x
          d.fy = event.y
        })
        .on('end', (event, d) => {
          if (!event.active) simulation.alphaTarget(0)
          d.fx = null
          d.fy = null
        })
      )

    // Circles
    node.append('circle')
      .attr('r', d => 8 + d.importance * 12)
      .attr('fill', d => typeColors[d.type] || '#4c6ef5')
      .attr('stroke', d => {
        const c = typeColors[d.type] || '#4c6ef5'
        return d3.color(c).brighter(0.5)
      })
      .attr('stroke-width', 2)
      .attr('opacity', 0.85)

    // Glow effect for high-importance
    node.append('circle')
      .attr('r', d => 12 + d.importance * 16)
      .attr('fill', d => typeColors[d.type] || '#4c6ef5')
      .attr('opacity', d => 0.08 + d.importance * 0.12)

    // Labels
    node.append('text')
      .text(d => d.label)
      .attr('x', 0)
      .attr('y', d => -(10 + d.importance * 12))
      .attr('text-anchor', 'middle')
      .attr('fill', '#C1C2C5')
      .attr('font-size', 11)
      .attr('font-family', 'Inter, sans-serif')

    // Click handler
    node.on('click', (event, d) => {
      if (onNodeClick) onNodeClick(d.data)
    })

    // Simulation tick
    simulation.on('tick', () => {
      link
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y)

      node.attr('transform', d => `translate(${d.x},${d.y})`)
    })

    return () => simulation.stop()
  }, [memories, onNodeClick])

  return (
    <svg
      ref={svgRef}
      className="w-full h-full"
      style={{ background: '#141517' }}
    />
  )
}