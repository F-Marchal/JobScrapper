# SQL Related classes
This folder contains a number of class which have 
for purpose provide help using SQLite through `SQLAlchemy`.

---

## command_formatter.py
Provide tools to ease the use of `querry.filter()`.
### CommandFormater
An object made to wrapp a `ClauseElement` but can also wrap any `Callable`
That might be use in `querry.filter()`. The primary goal of this object is to link strings passed
by users during database interrogation with true usable filters for `querry.filter()`.

This class provide :
- A help that describe what the encapsulated element does. This help might be displayed to users who use `job_scrapper/main.py`
- A short string ("symbol") that represent what the encapsulated element does. This element is used by the CommandFormater to understand command gave by user in  `job_scrapper/main.py`
- A cast function to transform a string into one or multiple types supported by the encapsulated element.

### Global variables
#### COMPARISON_OPE
Contains a number of `CommandFormater` that can be used to compare column values and 
with a value (E.g : Column >= 1 ; Column == Value; Column != Value ...)

#### LOGICAL_OPE
Contains a number of `CommandFormater` that can be used as logical operators
(E.g : AND(Condition1, Condition2) ; OR(Condition1, Condition2)...)

---