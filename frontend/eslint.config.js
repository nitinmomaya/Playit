// Import js dependencies.
import js from '@eslint/js'
// Import globals dependencies.
import globals from 'globals'
// Import eslint-plugin-react-hooks dependencies.
import reactHooks from 'eslint-plugin-react-hooks'
// Import eslint-plugin-react-refresh dependencies.
import reactRefresh from 'eslint-plugin-react-refresh'
// Import typescript-eslint dependencies.
import tseslint from 'typescript-eslint'
// Import config dependencies.
import { defineConfig, globalIgnores } from 'eslint/config'

// Export this module's public entry point.
export default defineConfig([
  globalIgnores(['dist']),
  {
    // Set the files option/value.
    files: ['**/*.{ts,tsx}'],
    // Set the extends option/value.
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    // Set the languageOptions option/value.
    languageOptions: {
      // Set the globals option/value.
      globals: globals.browser,
    },
  },
])

/* File summary
 * - Combines JavaScript, TypeScript, hooks, and refresh lint rules.
 * - Uses browser globals and excludes generated dist output.
 */
