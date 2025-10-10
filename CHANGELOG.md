## v0.2.0 (2025-10-10)

### Feat

- **ScrapperObjectCore**: add comparaison methods
- **import_from_flat_file**: add a method that read flat files and load content into object
- **ScrapperObjectCore**: ScrapperObjectCore have now method to remove values from _distances / _metadata / _keywords / _time_stamps
- **ScrapperObjectCore.get_unique_file_name--->-get_unique_path**: get_unique_file_name has been renamed to get_unique_path. get_unique_path now works for both folders and files
- **ScrapperObjectCore**: add unflat method that recreate a ScrapperObjectCore from the outpout of flat
- **scrapper-object-core**: improve internal dict accessibility

### Fix

- **ScrapperObjectCore.workdir**: workdir is generated when used
- **JobObject-to_dict-content**: to_dict can contain float / int for keywords and distances issue #2

### Refactor

- **test_tools**: /test/test_tools content moved to ./tools and ./tests/tools
