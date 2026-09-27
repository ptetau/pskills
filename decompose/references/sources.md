# Sources

Where each idea in this skill comes from, and what it contributes. Quotes in the other
reference files were checked against these sources. Where only a reputable secondary
source was available, the entry says so.

## Walls: volatility-based decomposition

<!-- WALLS_SOURCES -->

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

<!-- BROWNFIELD_SOURCES -->
