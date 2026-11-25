# Evaluation set

Run each case in [the request set](response-pipe.json) with a fresh conversation. Where the prompt supplies prior context, establish those facts or preferences before sending the current request. Use the supplied example links as synthetic destinations. The cases can be scored without contacting a reviewer, editing a plan or sending an email.

Check the reply against the actual work. Can a returning reader tell which milestone was reached, who can go first and what result unlocks the next step? Compare each link to its stated destination. In the branching case, Finance waits for sign-off while Support can begin immediately. In the exact-output case, parse the whole reply as JSON and compare the resulting object.

The [structural result](results/2026-11-25-structural.json) records packaging checks. Installed-host behavioral replay remains pending. For that replay, record the host, plugin version, case IDs, observed activation and any differences from the expected behavior.
