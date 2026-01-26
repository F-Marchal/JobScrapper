import click
import re

from job_scrapper.scrapper_skeleton.scrapper_skeleton import JobScrapperSkeleton
import cloup

from job_scrapper.sql.tables.helpers.keyword_manager import KeywordManager, KeywordRegex
from job_scrapper.sql.tables import KeywordVersion

@cloup.group()
@click.pass_context
def manage_keywords(ctx):
    """Add, remove, describe keywords in database.
    In the context of this program, a 'keyword' is a sequence
    of text that you want to search inside each offer.
    Each keyword can be attached to multiple regexes.
    Each keyword + set of regex is attached to a version
    for debugging purposes."""
    km = JobScrapperSkeleton.get_keyword_manager()
    ctx.obj['keyword_manager'] = km

@manage_keywords.command()
@click.pass_context
@cloup.argument(
    'keywords',
    type=str,
    help="A list of keywords to check. If unfill, All keywords are used",
    nargs=-1,
    default=None,
)
def describe(ctx, keywords: tuple[str] | None):
    """Describe keyword(s) versions that can be selected. This command will display a tsv :
    - NAME) `keywords` name
    - VERSION) version number ;
    - SELECTED) Does this keyword version is searched inside job description ? ;
    - REGEXES) Regex searched inside job description"""
    manager: KeywordManager = ctx.obj["keyword_manager"]

    # Uses all keywords when `keywords` is None
    if not keywords:
        with JobScrapperSkeleton.get_maindb_session(workdir=ctx.obj["workdir"]) as session:
            keywords = manager.find_all_keywords(session=session)

    print("NAME\tVERSION\tSELECTED\tREGEXES")
    summary = {}
    for k in keywords:
        nb_of_k = _describe(ctx=ctx, manager=manager, keyword=k)
        summary[k] = nb_of_k

    print()
    print()
    print("Summary :")
    print("-", "\n- ".join([f"{i} version(s) found for {k}." for k, i in summary.items()]))

def _describe(ctx, manager: KeywordManager, keyword: str) -> int:
    with JobScrapperSkeleton.get_maindb_session(workdir=ctx.obj["workdir"]) as session:
        # Fetch version objects
        all_ver = session.query(
             KeywordVersion
         ).where(
             KeywordVersion.keyword == keyword
         ).all()

        # Describe each version object
        i = 0
        for ver_entry in all_ver:
            regexes = [reg_entr.regex for reg_entr in ver_entry.regex_entries]
            selected = manager.is_selected(session, ver_entry)
            version = ver_entry.version
            key = ver_entry.keyword
            reg = '\t'.join(regexes)
            print(f"{key}\t{version}\t{selected}\t{reg}")
            i += 1

        return i
NO_AUTO_SELECT_OPT = cloup.option(
    "--no-auto-select",
    is_flag = True,
    help = "The newly modified version will not be set as selected ."
           "(This new version will not be used to search keyword inside "
           "offers if you do not select it manually)",
)

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
    required=True,
)
@cloup.option(
    "-y",
    "--yes",
    is_flag=True,
    help="Assume yes when asked."
)
@cloup.option(
    "--new",
    is_flag=True,
    help="Regexes will be added to an empty set of regexes. Use this flag "
         "if you do not want to base your version on the selected one."
)
@NO_AUTO_SELECT_OPT
def add(ctx, keyword: str, regexes: tuple[str], yes: bool, no_auto_select: bool, new: bool):
    """Add one or more regexes to search inside job description.
    This will update the selected keyword version. Those keywords will be added to
    the set of keywords attached to the selected version."""
    failed = False
    manager: KeywordManager = ctx.obj["keyword_manager"]

    load_selected(
        ctx=ctx,
        keyword=keyword,
        manager=manager,
        new=new
    )

    for regex in regexes:
        try:
            manager.add_regex(keyword, regex)
        except re.error as e:
            print()
            print(e)
            failed = True

    print()
    if failed:
        print("THE DATABASE HAS NOT BE UPDATED.")
        exit(1)

    _commit_select_msg(
        ctx=ctx,
        keyword=keyword,
        manager=manager,
        yes=yes,
        no_auto_select=no_auto_select,
    )



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
@NO_AUTO_SELECT_OPT
def remove(ctx, keyword: str, regexes: tuple[str], yes: bool, no_auto_select: bool):
    """Remove one or more regexes to search inside job description."""
    manager: KeywordManager = ctx.obj["keyword_manager"]

    load_selected(
        ctx=ctx,
        keyword=keyword,
        manager=manager,
        new=False
    )

    if not regexes:
        regexes = ctx.obj["keyword_manager"].regexes(keyword)

    print()
    print(f"{len(regexes)} regexes will be removed.")

    for reg in regexes:
        ctx.obj["keyword_manager"].remove_regex(keyword, reg)
    print()

    _commit_select_msg(
        ctx=ctx,
        keyword=keyword,
        manager=manager,
        yes=yes,
        no_auto_select=no_auto_select,
    )

def load_selected(ctx, keyword: str, manager: KeywordManager, new: bool ):
    if new:
        print("No regex loaded from database. (new=True)")
        return

    with JobScrapperSkeleton.get_maindb_session(workdir=ctx.obj["workdir"]) as session:
        sel_ver = manager.retrieve_selected_keyword_version(session, keyword=keyword)
        if sel_ver is not None:
            print(f"Loading selected version... ({sel_ver})")
            ver = sel_ver.version_entry
        else:

            ver = manager.get_latest_version(session, keyword=keyword)
            if ver is None:
                print()
                print(f"No regex loaded from database. No version attached to '{keyword}'")
                return

            print(f"Loading latest version... ({ver})")



        manager.load(session, keyword_version=ver)
        loaded_regex =  manager.regexes(keyword)
        print()
        print(f"{len(loaded_regex)} regexes are attached to '{keyword}'.")
        print("\t- ", loaded_regex, sep="")




def _commit_msg(ctx, keyword, yes) -> dict[str, int]:
    keyword_regexes =  ctx.obj["keyword_manager"].regexes(keyword)
    print(f"'{keyword}' now correspond to {len(keyword_regexes)} regexes : ",)
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
        c_result = ctx.obj["keyword_manager"].commit(session)

        # result is returned. if we keep Version object AND we close session
        # by exiting the 'with', we will have a DetachedInstanceError
        result = {key: ver.version for key, ver in c_result.items()}
        print("Database updated.")

    return result


def _commit_select_msg(ctx, manager: KeywordManager, keyword: str, no_auto_select: bool, yes: bool):
    result = _commit_msg(ctx, keyword, yes)
    version = result[keyword]

    if no_auto_select:
        print(
            "This set of regexes has not been selected (`--no-auto-select`)"
        )
        return

    _set_version(ctx, manager, keyword, version)

def _set_version(ctx, manager: KeywordManager, keyword: str, version: int):
    with JobScrapperSkeleton.get_maindb_session(workdir=ctx.obj["workdir"]) as session:
        try:
            manager.set_selected_keyword_version(session, keyword=keyword, version=version)
        except KeyError:
            print(f"Unable to select version={version} for '{keyword}'. This version does not exist.")
            exit(1)

        print()
        print(
            "Set of regexes selected for future keyword research in job offers. ",
            f"(keyword={keyword}", f"version={version})",
        )


@manage_keywords.command()
@click.pass_context
@cloup.argument(
    'keyword',
    type=str,
    help="Targeted keyword.",
)
@cloup.argument(
    'version',
    type=int,
    help="Version number.",
)
def select(ctx, keyword: str, version: int):
    """Select the wanted version of the wanted keyword."""
    _set_version(ctx=ctx, manager=ctx.obj["keyword_manager"], keyword=keyword, version=version)

@manage_keywords.command()
@click.pass_context
@cloup.argument(
    'keyword',
    type=str,
    help="Targeted keyword.",
)
def unselect(ctx, keyword: str):
    """Unselect a keyword. This keyword will not be searched anymore in offers."""
    with JobScrapperSkeleton.get_maindb_session(workdir=ctx.obj["workdir"]) as session:
        r = ctx.obj["keyword_manager"].delete_selected_keyword_version(
            session=session,
            keyword=keyword
        )
        if r:
            print("Keyword deselected")
        else:
            print("Keyword wasn't selected.")