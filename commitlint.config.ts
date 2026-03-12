
const config = {
  extends: ['@commitlint/config-conventional'],
  ignores: [(commit: string) => commit.startsWith('chore(release):')],
};

export default config;
