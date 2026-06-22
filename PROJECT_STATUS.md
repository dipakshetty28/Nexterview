## New Direction Before next step

Before production hardening and multi-agent review, upgrade the candidate interview experience from a single-file editor to a repo-based corporate engineering simulation.

The platform should generate a small runnable demo project based on the selected tech stack.

Each scenario should include:
- multiple project files
- realistic folder structure
- seed data as JSON
- runnable app or API
- one or more intentional bugs
- one feature request
- candidate instructions
- tests or validation instructions
- Git branch submission flow

The candidate should edit multiple files in a VS Code-like editor.

On submission:
- the platform should create a branch
- commit candidate changes
- push branch to GitHub if GitHub integration is configured
- store branch URL / commit URL / PR URL when available
- still store submitted files in the database as fallback

The AI copilot should act like a real engineering assistant:
- answer questions directly
- suggest fixes
- provide code
- explain files
- help debug errors
- reason over the full project context
- never expose hidden rubric
- never claim it ran code unless it actually did

This is now a corporate-level interview platform, not a single-code-editor toy.