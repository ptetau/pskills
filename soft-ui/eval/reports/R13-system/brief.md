# R13 · System model of a subscription business

`model.json` describes a system-dynamics model of "Tīeke", a SaaS product. It holds the
variables (stocks, flows, and auxiliaries), the causal links between them with polarity
(+ or −), the named feedback loops, and a matrix of how strongly each team's work
affects each variable. `sim.csv` holds a 24-month simulation of the main stocks under
two scenarios: "baseline" and "double support staff".

Reader: the leadership team at a strategy offsite. They need to see the structure of the
system (what drives what, and which loops reinforce or balance), how the stocks change
over time in each scenario, and where each team has the most effect.
