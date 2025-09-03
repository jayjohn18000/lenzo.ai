// eslint.config.mjs
import js from '@eslint/js';
import tseslint from 'typescript-eslint';
import nextPlugin from '@next/eslint-plugin-next';
import reactHooks from 'eslint-plugin-react-hooks';
import react from 'eslint-plugin-react';
import globals from 'globals';
import unusedImports from 'eslint-plugin-unused-imports';


export default [
  // Ignore outputs, virtual env, and the config file itself
  { ignores: [
      'eslint.config.mjs',
      '.next/**','dist/**','build/**','out/**','node_modules/**',
      '.venv/**'                // ← your Python env
    ]},

  // Base JS recs
  js.configs.recommended,

  // TypeScript / React / Next rules for app code
  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      parser: tseslint.parser,
      parserOptions: {
        project: './tsconfig.json',
        tsconfigRootDir: new URL('.', import.meta.url).pathname,
        ecmaVersion: 2023,
        sourceType: 'module',
      },
      // Make browser globals available in components/pages
      globals: {
        ...globals.browser,
        console: 'readonly',
      },
    },
    plugins: {
      '@typescript-eslint': tseslint.plugin,
      '@next/next': nextPlugin,
      react, 'react-hooks': reactHooks,
      'unused-imports': unusedImports,            
    },
    settings: { react: { version: 'detect' } },
    rules: {
      ...nextPlugin.configs.recommended.rules,
      'unused-imports/no-unused-imports': 'error', // ② remove unused imports automatically
      '@typescript-eslint/no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
      'react/display-name': 'warn',
      'prefer-const': 'warn',
    },
  },

  // Server/runtime code with Node globals
  {
    files: [
      'next.config.*','postcss.config.*','tailwind.config.*',
      'scripts/**','app/api/**','lib/**','*.cjs','*.mjs'
    ],
    languageOptions: {
      globals: {
        ...globals.node,
        console: 'readonly',
      },
    },
    rules: {
      '@typescript-eslint/no-require-imports': 'off',
    },
  },

  // UI wrappers: allow empty interface extensions
  { files: ['components/ui/**'], rules: { '@typescript-eslint/no-empty-object-type': 'off' } },

  // Generated types
  { files: ['next-env.d.ts'], rules: { '@typescript-eslint/triple-slash-reference': 'off' } },

  // Temporarily loosen “any” while refactoring
  { files: ['lib/audit/**','lib/api/**','lib/chart-utils.ts'], rules: { '@typescript-eslint/no-explicit-any': 'warn' } },
]
