# Benchmark manifests

Manifests are canonical JSON and `manifest_hash` is SHA-256 over the complete
object excluding that field. They contain only frozen selectors and task-tree
hashes, never task instructions, tests, trajectories, or `solution/` content.

`smoke-v1.json` has exactly two selectors: one SkillEvolBench family with its
ordered `T1`--`T6` roles and one exact Terminal-Bench task. The harness expands
this to 21 primary attempts (7 trials × C0/C1/C2). `pilot-v1.json` has three
families and three Terminal tasks, expanding to 63 primary attempts.

After `protocol-v1` is created, a pilot run byte-compares its manifest with the
tag and refuses changed IDs, hashes, prompt bundle, lock, or runtime budget.
