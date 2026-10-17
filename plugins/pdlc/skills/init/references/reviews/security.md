# Remit: security

Default: yes

You judge if the change is safe.

- The code validates input from users, files, or the network as the requirements say,
  before it uses the input.
- There is no injection: the code builds commands, queries, paths, and HTML safely.
- There are no secrets in code, logs, or errors.
- Permissions and access checks are correct, and they fail closed.
- Each new dependency is necessary and trustworthy.
