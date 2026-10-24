// Import musicApi dependencies.
import type { PlaylistPreview, PlaylistResult } from '../../src/lib/musicApi'

// Describe the ChatMessage data contract.
export type ChatMessage = {
  // Define id in this data shape.
  id: string
  // Define role in this data shape.
  role: 'user' | 'assistant'
  // Define text in this data shape.
  text: string
  // Define contextText in this data shape.
  contextText?: string
  // Define progress in this data shape.
  progress: string[]
  // Define status in this data shape.
  status: 'streaming' | 'complete' | 'stopped' | 'error'
  // Define playlist in this data shape.
  playlist?: {
    // Define preview in this data shape.
    preview: PlaylistPreview
    // Define creating in this data shape.
    creating: boolean
    // Define result in this data shape.
    result: PlaylistResult | null
    // Define error in this data shape.
    error: string | null
  }
}

/* File summary
 * - Defines message roles, lifecycle status, and playlist UI state.
 * - Keeps model-context text separate from displayed catalog previews.
 */
