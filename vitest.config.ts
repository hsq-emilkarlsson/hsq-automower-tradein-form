import {defineConfig} from 'vitest/config';

export default defineConfig({
  test: {
    coverage: {
      enabled: true,
      exclude: ['src/main.ts', 'src/**/*.test.ts', 'src/**/*.generated.*'],
      include: ['src/**/*.ts'],
      thresholds: {
        statements: 100,
        branches: 100,
        functions: 100,
        lines: 100,
      },
    },
  },
});
