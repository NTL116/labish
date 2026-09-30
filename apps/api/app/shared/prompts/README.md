# Prompt Templates

All agent system instructions, structural system roles, and template context
formats live in this directory as plain text, markdown, or YAML files.

Rules:

- Never bake raw prompt strings directly into Python execution files.
- Load templates from this directory at runtime so prompts can be
  version-controlled, tested, and fine-tuned independently of backend logic.
- Name files after the agent or workflow that consumes them
  (e.g., `order_triage_agent.md`, `email_summarizer.yaml`).
