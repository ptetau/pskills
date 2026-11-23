# The chain: decompose, blueprint, pdlc

`/decompose`, `/blueprint`, and `pdlc` work as one chain for a new system. Each tool takes the
output of the tool before it. You can also use each tool alone.

| Step | Tool | The question | The output |
|---|---|---|---|
| 1 | `/decompose` | Where do the walls go? | `<name>.design.md` |
| 2 | `/blueprint` | What exactly gets built? | `<name>.blueprint.md` |
| 3 | `/pdlc:intake` | How does it become verified code? | specs, changes, checks, and code |

The commands, in order:

```
/decompose a notifications service
/blueprint notifications.design.md
/pdlc:init
/pdlc:intake notifications.blueprint.md
```

The same idea has a different name in each tool. This table gives the match:

| In the blueprint | In pdlc |
|---|---|
| The in-scope list of section 1 | "What and why" of the intent |
| An invariant, with its enforcement point | A requirement of the capability that enforces the rule |
| The error table: code, meaning, fault | The rows of `DES-errors`: code, meaning, whose fault |
| The signature of a method | The "Interface" of a change |
| A scenario (Given, when, then) | The acceptance lines of a requirement |
| An Engine or a ResourceAccess | A capability |
| A method of a Manager | A job |
| A decision marked `(assumed)` | The same mark, `(assumed)` |
| The fault words `caller`, `system`, and `outside service` | The same three words in `DES-errors` |

Four rules keep the chain consistent:

- The design and the blueprint are frozen inputs. After intake, the pdlc specs lead. To change
  the design later, run `/decompose` on the real code, then `/blueprint`, then
  `/pdlc:intake` again.
- The blueprint has no IDs. Intake gives each requirement its pdlc ID.
- The blueprint writes the mark `(assumed)` in plain form, with any reason outside the
  brackets. The pdlc merge check accepts that form, and any other mark that starts with
  `(assumed`.
- `/decompose` and `/blueprint` use the master writing check. It has a reading grade of 7 and
  a glossary rule. pdlc has a smaller check, with four rules.

