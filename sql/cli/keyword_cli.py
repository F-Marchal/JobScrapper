import click
import re
from job_scrapper.scrapper_skeleton.scrapper_skeleton import JobScrapperSkeleton
import cloup

from sql.tables.helpers.keyword_manager import KeywordManager, KeywordRegex
from sql.tables import KeywordVersion

@cloup.group()
@click.pass_context
def manage_keywords(ctx):
    """Add, remove, describe keywords in database.
    In the context of this program, a 'keyword' is a sequence
    of text that you want to search inside each offer.
    Each keyword can be attached to multiple regexes.
    Each keyword + set of regex is attached to a version
    for debugging purposes."""
    # Always target mainDB
    km = JobScrapperSkeleton.get_keyword_manager()
    print()
    print("Loading keywords from database...")
    with JobScrapperSkeleton.get_maindb_session(workdir=ctx.obj["workdir"]) as session:
         km.load_all(session)

    ctx.obj['keyword_manager'] = km

@manage_keywords.command()
@click.pass_context
@cloup.argument(
    'keywords',
    type=str,
    help="A list of keywords to check. If unfill, All keywords are used.",
    nargs=-1,
    default=tuple()
)
def describe(ctx, keywords: tuple[str]):
    """Returns version, regexes and whether a keyword is 'alive'.
    ALIVE) Does this keyword is searched inside job description ? ;
    VERSION) Current version number ;
    REGEXES) Regex searched inside job description ;"""
    manager: KeywordManager = ctx.obj["keyword_manager"]

    if not keywords:
        keywords = tuple(manager.keywords)

    print("NAME\tALIVE\tVERSION\tREGEXES")
    for key in keywords:
        try:
            regexes = manager.regexes(key)
        except KeyError:
            alive = "-"
            reg = ""
            ver = "-"
        else:
            alive = len(regexes) != 0
            reg = '\t'.join(regexes)
            with JobScrapperSkeleton.get_maindb_session(workdir=ctx.obj["workdir"]) as session:
                ver = manager.get_latest_version(session, key).version
        print(f"{key}\t{alive}\t{ver}\t{reg}")

@manage_keywords.command()
@click.pass_context
@cloup.argument(
    'keyword',
    type=str,
    help="A keywords to check.",
)
def history(ctx, keyword: str):
    """Returns the all versions attached to a keyword.
    ALIVE) Does this keyword is searched inside job description ? ;
    VERSION) Current version number ;
    REGEXES) Regex searched inside job description"""
    with JobScrapperSkeleton.get_maindb_session(workdir=ctx.obj["workdir"]) as session:
        all_ver = session.query(
             KeywordVersion
         ).where(
             KeywordVersion.keyword == keyword
         ).all()
        print(f"{len(all_ver)} version(s) of '{keyword}' exist.")
        print()
        print("NAME\tALIVE\tVERSION\tREGEXES")
        for ver_entry in all_ver:
            regexes = [reg_entr.regex for reg_entr in ver_entry.regex_entries]
            alive = len(regexes) != 0
            version = ver_entry.version
            key = ver_entry.keyword
            reg = '\t'.join(regexes)
            print(f"{key}\t{alive}\t{version}\t{reg}")

@manage_keywords.command()
@click.pass_context
@cloup.argument(
    'keyword',
    type=str,
    help="Targeted keyword.",
)
@cloup.argument(
    "regexes",
    type=str,
    help="A list of pattern to check inside job description. Each time "
         "a pattern is found, the counter attached to <keyword> is raised by 1.",
    nargs=-1,
)
@cloup.option(
    "-y",
    "--yes",
    is_flag=True,
    help="Assume yes when asked."
)
def add(ctx, keyword: str, regexes: tuple[str], yes: bool):
    """Add one or more regexes to search inside job description."""
    failed = False
    for regex in regexes:
        try:
            ctx.obj["keyword_manager"].add_regex(keyword, regex)
        except re.error as e:
            print()
            print(e)
            failed = True

    print()
    if failed:
        print("THE DATABASE HAS NOT BE UPDATED.")
        exit(1)

    _commit_msg(ctx, keyword, yes)



@manage_keywords.command()
@click.pass_context
@cloup.argument(
    'keyword',
    type=str,
    help="Targeted keyword.",
)
@cloup.argument(
    "regexes",
    type=str,
    help="A list of pattern that should not be check inside job description. Each time "
         "a pattern is found, the counter attached to <keyword> is raised by 1. If unfill, "
         "all regexes are removed.",
    nargs=-1,
    default=tuple()
)
@cloup.option(
    "-y",
    "--yes",
    is_flag=True,
    help="Assume yes when asked."
)
def remove(ctx, keyword: str, regexes: tuple[str], yes: bool):
    """Remove one or more regexes to search inside job description."""
    if not regexes:
        regexes = ctx.obj["keyword_manager"].regexes(keyword)

    for reg in regexes:
        ctx.obj["keyword_manager"].remove_regex(keyword, reg)

    _commit_msg(ctx, keyword, yes)


def _commit_msg(ctx, keyword, yes):
    keyword_regexes =  ctx.obj["keyword_manager"].regexes(keyword)
    print(f"'{keyword}' is now composed of {len(keyword_regexes)} regexes : ",)
    print(keyword_regexes)
    print()
    if not yes:
        print("Is that what you wanted ?")
        confirm = input("Y / N : ")
    else:
        confirm = "yes"
    print()

    if confirm.lower()  not in ("y", "yes"):
        print("THE DATABASE HAS NOT BE UPDATED.")
        exit(2)

    with JobScrapperSkeleton.get_maindb_session(workdir=ctx.obj["workdir"]) as session:
        ctx.obj["keyword_manager"].commit(session)
        print("Database updated.")


