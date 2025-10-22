# ClauseElementWrapper (wrapper_clause_element.py)
An object made to wrapp a `ClauseElement` but can also wrap any `Callable`
That might be use in `querry.filter()`. The primary goal of this object is to link strings passed
by users during database interrogation with true usable filters for `querry.filter()`.

This class provide :
- A help that describe what the encapsulated element does. This help might be displayed to users who use `job_scrapper/main.py`
- A list short string ("symbols") that represent what the encapsulated element does. This element is used by the CommandFormater to understand command gave by user in  `job_scrapper/main.py`
---
## ComparisonWrapper (wrapper_comparison)
Specialise `ClauseElementWrapper` to handle comparisons element e.g `<=`, `==`, `col.ilike`...

This class provide:
- A list of type that are accepted by the comparisons element (`date`, `int`, `str`, ...)
- A method to cast a string into one of those specified type.

Furthermore, `wrapper_comparison` contains two global variables :
- `[OPERATION]_WRAPPER` : A number of `ComparisonWrapper` initialed to perform operations (`<=`, `==`, `col.ilike`...)
- `COMPARISON_WRAPPERS` : A list of all `ComparisonWrapper` initialised inside this file
- `STRING_TO_COMPARISON_WRAPPERS` : A dictionary which associate each "symbols" with a `ComparisonWrapper`
---
## LogicalWrapper (wrapper_logical)
Specialise `ClauseElementWrapper` to handle logical comparison e.g `and`, `xor`, `or not`...

`wrapper_comparison` contains two global variables :
- `[LOGIC]_WRAPPER` : A number of `LogicalWrapper` initialised to perform logical operations (`and`, `xor`, `or not`...)
- `COMPARISON_WRAPPERS` : A list of all `LogicalWrapper` initialised inside this file
- `STRING_TO_COMPARISON_WRAPPERS` : A dictionary which associate each "symbols" with a `LogicalWrapper`
