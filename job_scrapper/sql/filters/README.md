# SQL Filters generator helper
The goal is to propose a way for the user to define sql filter when he requests 
information related to jobs.

At this time, the user is expected to define a number of `FilterPart` using
strings of text :
1. `<Column name>` --> Display the column in the result
2. `<Column name>::<Comparator (==, <=, ilike, ...)>::<Value>` --> Display the column and filter results
3. `<Operator (&, |, ^, |~, ...)>::<Column name>::<Comparator (==, <=, ilike, ...)>::<Value>` "
--> Display the column and filter results

4. `<Parenthesis (')', '(', ')(')>::<Operator (&, |, ^, |~, ...)>::<Column name>::<Comparator (==, <=, ilike, ...)>::<Value>`
--> Display the column and filter results

As an example : `url::Contains::https` will create a filter that only keep job with a url
that contains `"https"`

---
# FilterGenerator (`filter_generator.py`)
This class is supposed to construct a filter that can be used inside a sqlAlchemy query objet
from `FilterPart`

---
# FilterPart (`filter_part.py`)
This class is able to parse a string and extract all data required to build a filter
(column name, operators...). This class uses wrapper from `sql/wrappers/` to achieve 
this goal. 

If you need to add support for new operators update `sql/wrappers/`
