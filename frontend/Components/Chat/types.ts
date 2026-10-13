export type ChatMessage = {
  id: string
  role: 'user' | 'assistant'
  text: string
  progress: string[]
  status: 'streaming' | 'complete' | 'stopped' | 'error'
}