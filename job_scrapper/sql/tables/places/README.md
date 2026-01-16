# Places

This folder should contain files that define table related to geographic localisation.

---

## Distances (`distances.py`)
The `Distances` table contains distances between two places (a reference and a job 
localisation). The distance can be `NULL` if the distance between the two places can not 
be computed.

---
## Places (`places.py`)
Table that contains coordinate of a number of localisations. `Places.sql_distance`
allows to compute distances between two localisation during the request of the database.
`Places.get_column_distance_to_self` allows to add a column that contains distances
between a job and a place to the result of a query.