import { useEffect, useSyncExternalStore } from 'react'
import type { Track } from './api'

/** Store simples de faixas atualizadas em tempo real pelo WebSocket. */
type Listener = () => void
const tracks = new Map<string, Track>()
const listeners = new Set<Listener>()
let version = 0

function notify() {
  version++
  listeners.forEach((l) => l())
}

export function upsertTracks(list: Track[]) {
  list.forEach((t) => tracks.set(t.id, t))
  notify()
}

export function removeTrack(id: string) {
  tracks.delete(id)
  notify()
}

export function getTrack(id: string) {
  return tracks.get(id)
}

export function allTracks() {
  return [...tracks.values()]
}

export function useStoreVersion() {
  return useSyncExternalStore(
    (l) => {
      listeners.add(l)
      return () => listeners.delete(l)
    },
    () => version,
  )
}

let ws: WebSocket | null = null
let connected = false
const connListeners = new Set<Listener>()

function connect() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  ws = new WebSocket(`${proto}://${location.host}/ws`)
  ws.onopen = () => {
    connected = true
    connListeners.forEach((l) => l())
  }
  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data)
    if (msg.type === 'track') upsertTracks([msg.track])
  }
  ws.onclose = () => {
    connected = false
    connListeners.forEach((l) => l())
    setTimeout(connect, 1500)
  }
}

export function useLiveConnection() {
  useEffect(() => {
    if (!ws) connect()
  }, [])
  return useSyncExternalStore(
    (l) => {
      connListeners.add(l)
      return () => connListeners.delete(l)
    },
    () => connected,
  )
}
