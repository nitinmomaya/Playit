// Enable React JSX transforms and development refresh.
import react from '@vitejs/plugin-react'
// Provide typed Vite configuration.
import { defineConfig } from 'vite'

// https://vite.dev/config/
// Export the configuration consumed by Vite's CLI.
export default defineConfig({
  // Apply React support without adding an API proxy.
  plugins: [react()],
})

/* File summary
 * - Configures the frontend development server and build tool.
 * - Enables React support; API hosts remain in the Axios modules.
 */
