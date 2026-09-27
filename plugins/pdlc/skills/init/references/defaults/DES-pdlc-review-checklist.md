# DES-pdlc-review-checklist · What review checks

Status: agreed · Default: yes · Ask at init: no

## Rule

A change passes review only if:

1. It only touches the files its change spec lists.
2. It stays inside its one job, capability or design spec. A job change never edits a
   capability.
3. Every acceptance check is met, and a check really proves it. A check that can't fail
   doesn't count.
4. It follows every design spec the change lists.
5. Every commit has its trailers, and every check names its requirement ID.

## Why

The same checklist on every change keeps review fair and fast.
