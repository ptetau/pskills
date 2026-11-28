# R7 · Git volatility of the billing service

/decompose measured volatility from the git history of the billing service.
`churn.csv` holds the lines changed for each file in each week, and `commits.csv` holds the
commit count for each day.

Reader: the architect. They need to see which files change most and together, when the
change happened, and which files are hot spots to put behind a wall.
