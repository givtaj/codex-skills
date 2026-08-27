# Privacy

This repository currently distributes instruction-only skills and template assets. It does not include an MCP server, bundled remote service, analytics client, telemetry code, or embedded credentials, and the repository itself does not collect or transmit user data.

An installed skill can guide ChatGPT or Codex to inspect information that the user and host environment make available. The host's permissions, sandbox, connected apps, and source-system access controls still apply. `status-review-dashboard` keeps reviews read-only unless the user explicitly requests a change.

`github-repository-guardrails` can guide the host to use the user's existing GitHub CLI or API access to read repository metadata, issues, pull requests, linked Projects, fields, and items. When separately authorized, it can also create or update repository files, issues, Projects, links, fields, or items. Those operations transmit selected data to GitHub under the user's GitHub account, organization policies, credentials, and permissions. The skill forbids token display, raw authentication logging, credential-store inspection, and copying unrelated private data into reusable or public artifacts.

Review each future plugin's manifest, skills, scripts, dependencies, and privacy statement before installation. A plugin that later adds a bundled network service or data-collecting component must update this document and its release notes before publication.
