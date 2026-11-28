# R10 · Dependency audit

An audit of the "web" app found the vulnerable packages in `vulns.json`. `tree.txt` holds
the dependency path from the app to each vulnerable package.

Reader: the security lead. They need the count by severity, each vulnerable package with
its fix version, and how each one gets into the app (direct or through which parent), so
they can plan the upgrades.
