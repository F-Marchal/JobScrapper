# Job extension
Main  `Job` table is not exhaustive. In order to be able to store more contextual information
without having a huge `Job` table with many null attributes, table that extend
Jobs are define in this directory.

---
##  JobExtraBase (`job_extra_base.py`)
This class inherit from BaseTable and define most of the behavior expected by 
table that extend the `Job` table such as foreign key structures.

WARNING : Relationship should be defined in BOTH `Job` table and table that inherit `JobExtraBase`.

---
## Keywords (`keywords.py`)
The `Keyword` table associate keywords contained inside a job offer and a number of occurrences.
The `NULL` value can be used for occurrences and is expected to represent that an error
occurred during keyword research.

---
## TimeStamps (`time_stamps.py`)
The `TimeStamps` table associate a label with a date (`YYYY-MM-JJ HH:MM:SS`). This table
is meant to contain time stamps related to the life of this job offer. This includes
without being limited to :
- First time this offer has been sighted
- Last time this offer has been sighted
- Last time that Keywords has been searched inside a job offer

---
## Metadata (`metadata.py`)
The `Metadata` table associate keywords a key (any string) and a value (any string).
This table is supposed to store anything related to a job offer that does not 
fit inside other `JobExtraBase`.

