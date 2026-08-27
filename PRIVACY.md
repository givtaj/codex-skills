# Privacy

This repository currently distributes instruction-only skills. It does not include an MCP server, remote service, analytics client, or telemetry code, and the repository itself does not collect or transmit user data.

An installed skill can guide ChatGPT or Codex to inspect information that the user and host environment make available. The host's permissions, sandbox, connected apps, and source-system access controls still apply. `status-review-dashboard` instructs the host to keep reviews read-only unless the user explicitly requests a change.

Review each future plugin's manifest, skills, scripts, dependencies, and privacy statement before installation. A plugin that later adds a network service or data-collecting component must update this document and its release notes before publication.
