import os


def get_unique_path(file_path: str, ext: str = "") -> str:
    """
    Give a filename that does not exist.
    if <file_path>.<ext> exist, <file_path>-<#>.<ext> will be tested. <#> is incremented
    until an unoccupied file name is found.
    :param str file_path: folder/filename
    :param str ext: file extension that should be added to  folder/filename (-->  folder/filename.ext)
    :return:
    """
    if ext and ext[0] != ".":
        ext = "." + ext

    default_name = file_path + ext

    if not os.path.exists(file_path + ext):
        return default_name

    counter = 1
    filename = file_path + "-{}" + ext
    while os.path.exists(filename.format(counter)):
        counter += 1

    return filename.format(counter)
