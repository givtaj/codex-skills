<!-- github-repository-guardrails:start -->
## Project management guardrails

Read `.github/repository-guardrails.conf` before repository-changing work and follow only its selected surfaces.

1. Read the selected plan, status, task, and outcome records before changing their state.
2. Reuse one work item and the repository's identifier convention across selected surfaces. Never invent an issue number.
3. Record only sanitized intent when that surface is selected—never a transcript, secret, private URL, credential, or raw command response.
4. Keep only the fields this repository has chosen current, including acceptance criteria, risks, verification, outcome decision, and next action.
5. Preview external writes and obtain the required authority. Keep transient Project and API identifiers out of generic configuration.
6. Run the repository's selected local and GitHub checks before closeout.
7. Follow the repository's existing status model and definition of done; do not claim completion without its required evidence.

Never display tokens, dump environments, inspect credential or private-key material, or persist raw authentication output.
<!-- github-repository-guardrails:end -->
