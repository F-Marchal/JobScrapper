# SQL tables

This folder is expected to contain :
- files that define main sql table
- folders that define secondary sql table

---
## BaseTable (`base_table`)
`base_table` define standard option that should be attached to sql table such as
representation helper methods (`to_dict()`, `flat()`, ...), a session generator and commit
sanitization.

---
## Jobs
Main table that describe job offers. This table is completed by tables defined inside
`job_extension`. This table should contain expected to be included inside most 
job offers such as the localisation, the type of contract, the title ...

job offer's url is used as primary key which can lead to duplicates inside the database
if the same offer has multiple url.