# Sources

Where each idea in this skill comes from, and what it contributes. Quotes in the other
reference files were checked against these sources. Where only a reputable secondary
source was available, the entry says so.

## Walls: volatility-based decomposition

| Source | Contributes |
|--------|-------------|
| David Parnas, "On the Criteria To Be Used in Decomposing Systems into Modules", CACM 1972 — <https://www.win.tue.nl/~wstomv/edu/2ip30/references/criteria_for_modularization.pdf> | The original argument: modules hide design decisions likely to change, not steps in a flowchart; the KWIC comparison; hide processing order in one module |
| Juval Löwy, *Righting Software* (2019), ch. 2 excerpt — <https://www.informit.com/articles/article.aspx?p=2995357> (and `&seqNum=2`, `&seqNum=3`) | Against functional and domain decomposition; decompose based on volatility; volatile vs variable; the two axes; solutions masquerading as requirements; the nature of the business; speculative design; design for competitors |
| Löwy, "Righting Software" slides, SDD 2022 — <http://sddvault.s3.amazonaws.com/presentation-slides/sdd2022/Righting%20Software.pdf> | The component taxonomy (Clients, Managers, Engines, ResourceAccess, Resources, Utilities); atomic business verbs vs CRUD |
| IDesign, "The IDesign Method" (2010) and management overview — <https://www.idesign.net/assets/documents/IDesign-Method-Management-Overview.pdf> | Closed architecture; call chains over the layer diagram; small sets of composable components; authenticate and authorize at every crossing of a service boundary |
| Löwy on SE Radio 407 (2020) — <https://se-radio.net/2020/04/episode-407-juval-lowy-on-righting-software/>; InfoQ review and Q&A — <https://www.infoq.com/articles/book-review-righting-software/> | "Features are aspects of integration, not implementation"; composable design; core use cases; about ten building blocks; the prime directive |
| Book passages quoted by readers (secondary, with page or Kindle locations): coderanch threads — <https://coderanch.com/t/729242/engineering/Righting-Software-Core-Cases>; Bookey summary — <https://cdn.bookey.app/files/pdf/book/en/righting-software.pdf>; right-software-skill notes — <https://github.com/liberlux47/right-software-skill/blob/main/references/method.md>; dev.to walkthrough — <https://dev.to/ujjwall-r/system-design-example-using-the-method-j6g> | Sequence vs activity; Engines as Strategy; call-rule relaxations and don'ts (only Managers publish; Clients and Managers may subscribe); the queue proxy as ResourceAccess; naming; size heuristics and the Manager:Engine ratio; "almost expendable" Managers; volatility decreasing down the layers; the cappuccino-machine Utility test; workflow Managers |
| Mary Branscombe, ZDNet review of *Righting Software* (2020) — <https://www.zdnet.com/article/righting-software-book-review-building-blocks-for-software-architects/> | Criticisms: opinionated, heuristic numbers, little on modern delivery practice |
| Robert C. Martin, *Clean Architecture* (2017) — component principles summarized at <https://github.com/serodriguez68/clean-architecture/blob/master/part-4-component-principles.md>; "The Single Responsibility Principle" (2014) — <https://blog.cleancoder.com/uncle-bob/2014/05/08/SingleReponsibilityPrinciple.html>; "Design Principles and Design Patterns" (2000) — <https://staff.cs.utu.fi/~jounsmed/doos_06/material/DesignPrinciplesAndPatterns.pdf> | The CCP, SRP ("one actor"), and SAP wordings quoted are from *Clean Architecture*; "the reasons for change are people" is from the 2014 essay; SDP ("depend in the direction of stability") from 2000 |
| Gamma, Helm, Johnson and Vlissides, *Design Patterns* (1994), §1.8, as quoted in *Design Patterns Explained* — <https://www.informit.com/articles/article.aspx?p=1398602> | "Encapsulate the concept that varies" |

## Bricks: orthogonal primitives

| Source | Contributes |
|--------|-------------|
| Eric S. Raymond, *The Art of Unix Programming*, ch. 4 "Orthogonality" — <http://www.catb.org/esr/writings/taoup/html/ch04s02.html> | Definition of orthogonality ("each action changes just one thing"); the SPOT rule; "no junk, no confusion" for data models |
| Raymond, ch. 1 "Basics of the Unix Philosophy" — <http://www.catb.org/esr/writings/taoup/html/ch01s06.html> | McIlroy's summary; the rules of Modularity, Composition, Separation (policy from mechanism), Representation, Extensibility |
| Doug McIlroy, 1964 pipes memo — <https://9p.io/cm/cs/who/dmr/mdmpipe.html> | "connecting programs like garden hose": composition as the goal |
| Hunt and Thomas, *The Pragmatic Programmer*, "Orthogonality" (secondary: <https://benforshey.com/the-pragmatic-programmer-chapter-2/>); Artima interview — <https://www.artima.com/intv/dry.html> | The change-count test ("how many modules are affected? … one"); the helicopter analogy |
| ALGOL 68 Revised Report, §0.1.2 "Orthogonal design" — <https://www.algol68-lang.org/docs/algol68-revised-report.pdf> | Few primitive concepts, applied orthogonally, for maximum expressive power |
| Wulf et al., "HYDRA: The Kernel of a Multiprocessor Operating System", CACM 1974 — <https://homes.cs.washington.edu/~arvind/cs422/doc/hydra.pdf>; Levin et al., "Policy/Mechanism Separation in Hydra", SOSP 1975 | Separation of mechanism and policy |
| Rich Hickey, "Simple Made Easy", 2011 — transcript <https://github.com/matthiasn/talk-transcripts/blob/master/Hickey_Rich/SimpleMadeEasy.md> | Compose vs complect; the who/what/when/where/why/how breakdown; queues instead of direct calls; rules instead of conditionals |
| John Ousterhout, *A Philosophy of Software Design* (secondary: <https://danlebrero.com/2021/02/24/philosophy-of-software-design-summary/>); CS190 notes — <https://web.stanford.edu/~ouster/cgi-bin/cs190-winter18/lecture.php?topic=modularDesign> | Deep modules; somewhat general-purpose interfaces and the three questions; information leakage; define errors out of existence |
| Abelson and Sussman, *SICP*, §1.1 and §2.2 — <https://mitp-content-server.mit.edu/books/content/sectbyfn/books_pres_0/6515/sicp.zip/full-text/book/book-Z-H-10.html> | Primitives, means of combination, means of abstraction; the closure property; sequences as conventional interfaces |
| Alan Perlis, *Epigrams on Programming*, #9 — <https://www.cs.yale.edu/homes/perlis-alan/quotes.html> | "100 functions on one data structure": the shared contract |
| Gary Bernhardt, "Functional Core, Imperative Shell" (2012) and "Boundaries" (SCNA 2012) — <https://www.destroyallsoftware.com/talks/boundaries> | Pure core, I/O at the edges; plain values at component boundaries |
| Eric Normand, *Grokking Simplicity* — <https://livebook.manning.com/book/exploring-functional-programming/chapter-1> | Actions, calculations, data |
| Apache Beam programming guide — <https://beam.apache.org/documentation/programming-guide/>; Vector concepts — <https://vector.dev/docs/introduction/concepts/> | Sources, transforms, sinks; composite transforms as closure in practice |
| Hohpe and Woolf, *Enterprise Integration Patterns*, "Pipes and Filters" — <https://www.enterpriseintegrationpatterns.com/patterns/messaging/PipesAndFilters.html> | Add, omit, or rearrange filters without changing them |
| David Harel, "Statecharts: a visual formalism for complex systems", 1987 — <https://dubroy.com/refs/Statecharts_a_visual_formalism_for_complex_systems.pdf> | State machines as a first-class primitive |
| Werner Vogels, "10 Lessons from 10 Years of AWS", 2016 — <https://www.allthingsdistributed.com/2016/03/10-lessons-from-10-years-of-aws.html> | "Primitives not frameworks" |
| Andy Jassy, 2023 letter to shareholders (quoting the 2003 AWS vision) — <https://www.aboutamazon.com/news/company-news/amazon-ceo-andy-jassy-2023-letter-to-shareholders> | Primitives are indivisible and do one thing well; start from real customer problems |
| John Hughes, "Why Functional Programming Matters" — <https://www.cs.kent.ac.uk/people/staff/dat/miranda/whyfp90.pdf> | How you can divide a problem depends on how you can glue the pieces |
| David Parnas, "Designing Software for Ease of Extension and Contraction", 1979 (secondary: <https://blog.acolyer.org/2016/10/31/designing-software-for-ease-of-extension-and-contraction/>) | Minimal subset plus minimal increments; the warning about pipeline stages that can't be removed |
| Daniel Jackson, *The Essence of Software* (secondary: <https://newsletter.squishy.computer/p/concept-design-in-three-easy-steps>) | Independent concepts composed by synchronization |

**Guardrails**

| Source | Contributes |
|--------|-------------|
| Sandi Metz, "The Wrong Abstraction", 2016 — <https://sandimetz.com/blog/2016/1/20/the-wrong-abstraction> | Prefer duplication over the wrong abstraction; the inline-and-re-extract remedy |
| Don Roberts, rule of three, via Fowler's *Refactoring* (secondary: <https://en.wikipedia.org/wiki/Rule_of_three_(computer_programming)>) | Extract on the third occurrence |
| Martin Fowler, "Yagni", 2015 — <https://martinfowler.com/bliki/Yagni.html> | YAGNI covers presumptive features, not making code easy to change |
| Alex Papadimoulis, "The Inner-Platform Effect", 2006 — <https://thedailywtf.com/articles/The_Inner-Platform_Effect> | Over-customizable systems become a poor copy of their platform |
| Mike Hadlow, "The Configuration Complexity Clock", 2012 — <http://mikehadlow.blogspot.com/2012/05/configuration-complexity-clock.html> | Config → rules engine → DSL → hard-coding in a worse language |
| Berners-Lee and Mendelsohn, "The Rule of Least Power", W3C 2006 — <https://www.w3.org/2001/tag/doc/leastPower.html> | Use the least powerful language that works |
| Hyrum Wright, Hyrum's Law — <https://www.hyrumslaw.com/> | All observable behavior gets depended on |

## Subsystems in established codebases

| Source | Contributes |
|--------|-------------|
| Adam Tornhill, *Your Code as a Crime Scene* and *Software Design X-Rays* (2018); code-maat — <https://github.com/adamtornhill/code-maat> | Hotspots (change frequency × size); change coupling as a hidden dependency; the coupling formula and default thresholds used by `volatility.py` (min-revs 5, min-shared 5, min-coupling 30%, max-changeset 30); Tornhill, "Code as a Crime Scene", *Overload* 117 (2013) — <https://accu.org/journals/overload/21/117/tornhill_1835/>: thresholds are tuned per codebase, a two-to-three-month window for recent trends |
| CodeScene docs on change coupling and code age — <https://codescene.io/docs/guides/technical/change-coupling.html> | Coupling is neither good nor bad in itself; organize code by age |
| Graves, Karr, Marron and Siy, "Predicting Fault Incidence Using Software Change History", IEEE TSE 2000 — <https://cs.uwaterloo.ca/~m2nagapp/courses/CS846/1171/papers/graves_tse98.pdf> | Number of changes predicts faults better than length |
| Nagappan and Ball, "Use of Relative Code Churn Measures to Predict System Defect Density", ICSE 2005 — <https://www.microsoft.com/en-us/research/publication/use-of-relative-code-churn-measures-to-predict-system-defect-density/> | Relative churn separates fault-prone binaries with 89% accuracy |
| D'Ambros, Lanza and Robbes, "On the Relationship Between Change Coupling and Software Defects", WCRE 2009 — <https://www.inf.usi.ch/lanza/PUBS/P/DAmb2009e.pdf> | Change coupling correlates with defects more than complexity does |
| Cataldo et al., "Software Dependencies, Work Dependencies, and Their Impact on Failures", IEEE TSE 2009 — <https://herbsleb.org/web-pubs/pdfs/cataldo-software-2009.pdf> | Logical dependencies explain most of the variance in fault proneness |
| Rahman and Devanbu, "How, and Why, Process Metrics Are Better", ICSE 2013 — <https://research.cs.queensu.ca/home/ahmed/home/teaching/CISC880/F17/papers/HowAndWhyProcessMetricsAreBetter.pdf> | Process metrics beat code metrics for prediction |
| Michael Feathers, *Working Effectively with Legacy Code* (2004) — <https://www.informit.com/articles/article.aspx?p=359417&seqNum=3> | Seams and enabling points; the legacy code change algorithm; sprout and wrap |
| Martin Fowler, "Strangler Fig Application" (2004, rewritten 2024) — <https://martinfowler.com/bliki/StranglerFigApplication.html>; "Patterns of Legacy Displacement" — <https://martinfowler.com/articles/patterns-legacy-displacement/> | Growing a new system around an old one; transitional architecture; event interception; asset capture |
| Martin Fowler, "Branch by Abstraction" (2014) — <https://martinfowler.com/bliki/BranchByAbstraction.html>; Paul Hammant (2007) — <https://paulhammant.com/blog/branch_by_abstraction.html> | Replacing behavior in place while staying releasable |
| Eric Evans, *Domain-Driven Design Reference* (2015) — <https://www.domainlanguage.com/wp-content/uploads/2016/05/DDD_Reference_2015-03.pdf> | Anti-corruption layer (for the downstream side); conformist, open-host service, published language, separate ways; boundary around a big ball of mud |
| Melvin Conway, "How Do Committees Invent?", 1968 — <https://www.melconway.com/Home/Committees_Paper.html>; Fowler, "Conway's Law" — <https://martinfowler.com/bliki/ConwaysLaw.html> | Designs copy communication structures; the inverse Conway maneuver |
| Skelton and Pais, *Team Topologies* (2019), fracture planes (secondary: <https://brain.mikecordell.com/fracture-planes>) | Change cadence as a natural split line |
| Hyrum's Law — <https://www.hyrumslaw.com/> | Implicit behavior at a seam is part of the contract |

## Diagrams and plain language

| Source | Contributes |
|--------|-------------|
| Simon Brown, the C4 model — <https://c4model.com> (abstractions, diagrams, notation, checklist) | The four levels; container and component definitions ("it's the container that's the deployable unit"); draw component diagrams only when they add value; titles, keys, typed elements, labelled one-way arrows; "notation independent" |
| Simon Brown, "Modular monolith" — <https://simonbrown.je/modular-monolith/> | Well-defined components in a monolith are a stepping stone to microservices: choosing containers is a separate decision |
| Mermaid, C4 diagrams — <https://mermaid.js.org/syntax/c4.html> | C4Context and C4Container syntax (experimental; no automatic layout; no legend), so component diagrams are drawn as C4-style flowcharts |
| GitHub, creating diagrams — <https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-diagrams> | Mermaid renders in GitHub Markdown |
| Kincaid, Fishburne, Rogers and Chissom, "Derivation of New Readability Formulas" (1975) — <https://stars.library.ucf.edu/istlibrary/56/> | The Flesch–Kincaid grade level that `readability.py` reports |

