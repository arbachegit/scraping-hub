/**
 * Graph Algorithms — client-side computations for graph analysis.
 * Degree/Betweenness/PageRank centrality, BFS shortest path, ego network extraction.
 */

import type { GraphNode, GraphEdge } from './types';

type AdjList = Map<string, { neighbor: string; edgeId: string }[]>;

function edgeEndpoints(e: GraphEdge): [string, string] {
  const s = typeof e.source === 'object' ? e.source.id : e.source;
  const t = typeof e.target === 'object' ? e.target.id : e.target;
  return [s, t];
}

function buildAdjList(nodes: GraphNode[], edges: GraphEdge[]): AdjList {
  const adj: AdjList = new Map();
  for (const n of nodes) adj.set(n.id, []);
  for (const e of edges) {
    const [s, t] = edgeEndpoints(e);
    adj.get(s)?.push({ neighbor: t, edgeId: e.id });
    adj.get(t)?.push({ neighbor: s, edgeId: e.id });
  }
  return adj;
}

/** Degree centrality: count of edges per node, normalized 0-1 */
export function degreeCentrality(nodes: GraphNode[], edges: GraphEdge[]): Map<string, number> {
  const counts = new Map<string, number>();
  for (const n of nodes) counts.set(n.id, 0);
  for (const e of edges) {
    const [s, t] = edgeEndpoints(e);
    counts.set(s, (counts.get(s) || 0) + 1);
    counts.set(t, (counts.get(t) || 0) + 1);
  }
  const max = Math.max(1, ...counts.values());
  const result = new Map<string, number>();
  for (const [id, c] of counts) result.set(id, c / max);
  return result;
}

/** Betweenness centrality: fraction of shortest paths through each node */
export function betweennessCentrality(nodes: GraphNode[], edges: GraphEdge[]): Map<string, number> {
  const adj = buildAdjList(nodes, edges);
  const bc = new Map<string, number>();
  for (const n of nodes) bc.set(n.id, 0);

  for (const s of nodes) {
    // BFS from s
    const dist = new Map<string, number>();
    const sigma = new Map<string, number>(); // # shortest paths
    const pred = new Map<string, string[]>();
    const stack: string[] = [];

    dist.set(s.id, 0);
    sigma.set(s.id, 1);
    const queue: string[] = [s.id];

    while (queue.length > 0) {
      const v = queue.shift()!;
      stack.push(v);
      const d = dist.get(v)!;
      for (const { neighbor: w } of adj.get(v) || []) {
        if (!dist.has(w)) {
          dist.set(w, d + 1);
          queue.push(w);
        }
        if (dist.get(w) === d + 1) {
          sigma.set(w, (sigma.get(w) || 0) + (sigma.get(v) || 0));
          if (!pred.has(w)) pred.set(w, []);
          pred.get(w)!.push(v);
        }
      }
    }

    const delta = new Map<string, number>();
    for (const n of nodes) delta.set(n.id, 0);
    while (stack.length > 0) {
      const w = stack.pop()!;
      for (const v of pred.get(w) || []) {
        const d = (delta.get(v) || 0) + ((sigma.get(v) || 1) / (sigma.get(w) || 1)) * (1 + (delta.get(w) || 0));
        delta.set(v, d);
      }
      if (w !== s.id) bc.set(w, (bc.get(w) || 0) + (delta.get(w) || 0));
    }
  }

  // Normalize
  const max = Math.max(1, ...bc.values());
  const result = new Map<string, number>();
  for (const [id, v] of bc) result.set(id, v / max);
  return result;
}

/** PageRank: iterative computation */
export function pageRank(nodes: GraphNode[], edges: GraphEdge[], iterations = 20, damping = 0.85): Map<string, number> {
  const n = nodes.length;
  if (n === 0) return new Map();

  const adj = buildAdjList(nodes, edges);
  const outDegree = new Map<string, number>();
  for (const node of nodes) outDegree.set(node.id, (adj.get(node.id) || []).length);

  let rank = new Map<string, number>();
  for (const node of nodes) rank.set(node.id, 1 / n);

  for (let i = 0; i < iterations; i++) {
    const newRank = new Map<string, number>();
    for (const node of nodes) {
      let sum = 0;
      for (const { neighbor } of adj.get(node.id) || []) {
        const deg = outDegree.get(neighbor) || 1;
        sum += (rank.get(neighbor) || 0) / deg;
      }
      newRank.set(node.id, (1 - damping) / n + damping * sum);
    }
    rank = newRank;
  }

  // Normalize 0-1
  const max = Math.max(1e-10, ...rank.values());
  const result = new Map<string, number>();
  for (const [id, v] of rank) result.set(id, v / max);
  return result;
}

/** BFS shortest path between two nodes. Returns array of node IDs or null. */
export function shortestPath(nodes: GraphNode[], edges: GraphEdge[], sourceId: string, targetId: string): string[] | null {
  if (sourceId === targetId) return [sourceId];
  const adj = buildAdjList(nodes, edges);
  const visited = new Set<string>();
  const parent = new Map<string, string>();
  const queue: string[] = [sourceId];
  visited.add(sourceId);

  while (queue.length > 0) {
    const v = queue.shift()!;
    for (const { neighbor } of adj.get(v) || []) {
      if (visited.has(neighbor)) continue;
      visited.add(neighbor);
      parent.set(neighbor, v);
      if (neighbor === targetId) {
        // Reconstruct path
        const path: string[] = [targetId];
        let cur = targetId;
        while (parent.has(cur)) {
          cur = parent.get(cur)!;
          path.unshift(cur);
        }
        return path;
      }
      queue.push(neighbor);
    }
  }
  return null;
}

/** Extract ego network: node + all neighbors within `hops` distance */
export function egoNetwork(nodes: GraphNode[], edges: GraphEdge[], centerId: string, hops: number): Set<string> {
  const adj = buildAdjList(nodes, edges);
  const visited = new Set<string>();
  const queue: [string, number][] = [[centerId, 0]];
  visited.add(centerId);

  while (queue.length > 0) {
    const [v, d] = queue.shift()!;
    if (d >= hops) continue;
    for (const { neighbor } of adj.get(v) || []) {
      if (!visited.has(neighbor)) {
        visited.add(neighbor);
        queue.push([neighbor, d + 1]);
      }
    }
  }
  return visited;
}

/** Filter edges by minimum strength threshold */
export function filterEdgesByThreshold(edges: GraphEdge[], threshold: number): Set<string> {
  const visible = new Set<string>();
  for (const e of edges) {
    if ((e.strength || 0) >= threshold) visible.add(e.id);
  }
  return visible;
}

/** Filter to top N% edges by strength (edge density control) */
export function filterEdgesByDensity(edges: GraphEdge[], topPercent: number): Set<string> {
  if (topPercent >= 100) return new Set(edges.map(e => e.id));
  const sorted = [...edges].sort((a, b) => (b.strength || 0) - (a.strength || 0));
  const count = Math.max(1, Math.ceil(sorted.length * topPercent / 100));
  return new Set(sorted.slice(0, count).map(e => e.id));
}
