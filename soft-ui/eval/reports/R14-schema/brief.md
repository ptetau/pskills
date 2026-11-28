# R14 · Database schema of the orders service

`schema.json` holds the tables of the orders database: each column with its type,
whether it is a primary key or a foreign key (and what it references), and whether it
can be null. `stats.csv` holds the row count, size, and index count of each table.

Reader: a new engineer in their first week. They need the shape of the data (which
tables relate to which, and how), the detail of each table, and which tables are big.
