# R3 · Design summary for the notifications subsystem

/decompose designed a notifications subsystem for an existing app. `design.json` holds
the result: the components and what each hides, the call edges, the data contracts, the
core use case as ordered steps, and a simulation of likely changes.

Reader: the engineers who will review the design tomorrow. They need to see the shape of
the system (who calls whom), how the core use case flows through it, the main data types,
and the evidence that each likely change lands in one place.
