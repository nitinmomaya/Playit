import type { PlaylistPreview, PlaylistResult } from '../../src/lib/musicApi'

export type ChatMessage = {
  id: string
  role: 'user' | 'assistant'
  text: string
  contextText?: string
  progress: string[]
  status: 'streaming' | 'complete' | 'stopped' | 'error'
  playlist?: {
    preview: PlaylistPreview
    creating: boolean
    result: PlaylistResult | null
    error: string | null
  }
}