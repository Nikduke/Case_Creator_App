# Starter Prompt For Codex

Paste this into Codex on the new laptop:

```text
You are working in this folder as the active project root for Case_Creator_App.

This project uses Git on the `main` branch. Do not rewrite shared history.

First read README.md, SETUP.md, PROJECT_CONTEXT.md, docs/APP_FUNCTIONAL_SPEC.md, and docs/PROJECT_JSON_GUIDE.md.

Then inspect the actual codebase before making changes. Verify documentation against code; do not assume docs are correct.

Use Anaconda Python with dedicated conda environment case-creator-app. Do not use base environment.

Before editing files, report your understanding of:
- app purpose;
- current folder structure;
- setup/run/test commands;
- relevant code modules for the requested task.

Use only relative paths in documentation.

Make small targeted changes. Avoid broad rewrites, unnecessary abstractions, duplicate logic, and style-only rewrites of working code.

Preserve existing behavior unless the requested change requires behavior change.

After meaningful changes, update relevant documentation and run the most relevant tests.
```
