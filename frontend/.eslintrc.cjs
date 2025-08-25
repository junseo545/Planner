module.exports = {
  root: true,
  env: { 
    browser: true, 
    es2020: true,
    node: true
  },
  extends: [
    'eslint:recommended',
    'plugin:react-hooks/recommended',
  ],
  ignorePatterns: ['dist', '.eslintrc.cjs'],
  parser: '@typescript-eslint/parser',
  plugins: ['react-refresh'],
  rules: {
    'react-refresh/only-export-components': [
      'warn',
      { allowConstantExport: true },
    ],
    'no-undef': 'off', // TypeScript가 처리하므로 비활성화
    'no-unused-vars': 'off', // TypeScript가 처리하므로 비활성화
    'no-redeclare': 'warn', // 경고로 변경
  },
  globals: {
    JSX: 'readonly',
    process: 'readonly',
    __dirname: 'readonly'
  }
}
