# pdlc

pdlc is a Claude Code plugin that runs the development lifecycle of a project. Your idea
becomes a spec. The spec becomes small changes. Each change is built test first, reviewed
by an independent reviewer, and traced back to the idea that asked for it. pdlc works in
any git project, for any language and any type of system.

pdlc runs only on a Sonnet 5.5 class model or above. On a lower model, each pdlc skill and
agent does no work.

## Start here

1. Add the marketplace and install the plugin:

   ```
   /plugin marketplace add ptetau/pskills
   claude plugin install pdlc@pskills --scope project
   ```

2. Open Claude Code in your project, and prepare the project. This creates the `pdlc/`
   folder:

   ```
   /pdlc:init
   ```

3. Ask for what you want, in your own words. pdlc runs every stage and stops only when it
   needs you:

   ```
   /pdlc:ship let users reset their password by email
   ```

`INSTALL.md` gives the full steps, and the options for a team.

## The stages

An item of work passes these stages in order. Each stage is a skill with its own command.

1. `/pdlc:intake`: changes your words into spec changes. Each new requirement starts as
   `proposed`.
2. `/pdlc:ready`: asks about each unclear item, and looks for contradictions.
3. `/pdlc:change`: divides the work into changes. Each change covers one job or one
   capability.
4. `/pdlc:acceptance`: a test writer writes the checks of the whole intent. pdlc locks
   them.
5. `/pdlc:tests`: a test writer writes the checks of one change, before any code. pdlc
   locks them.
6. `/pdlc:build`: a builder writes code until the locked checks pass. The builder cannot
   change the checks.
7. `/pdlc:verify`: runs the checks, and sends one packet to each independent reviewer.
8. `/pdlc:show`: records a GIF of the change, has the recording reviewed, and proposes
   the merge. You approve it.

## Other skills

- `/pdlc:conventions`: set or change how the project does a thing everywhere.
- `/pdlc:trace`: answer "why does this code exist?", and "what did this intent change?".
- `/pdlc:board`: show intents and changes as cards on a GitHub project or in Linear.
- `/pdlc:dashboard`: install the optional live dashboard.
- `/pdlc:upgrade`: bring the pdlc files of a project up to the installed version.

## Read more

- `INSTALL.md`: installation, the merge check for CI, the guard hooks, and how to update.
- `OUTLINE.md`: the design of pdlc, and the reasons for it.
- `../../plans/archive/build-pdlc-v1.plan.md`: the build record of version 1.
