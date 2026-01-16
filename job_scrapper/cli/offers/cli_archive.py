import click
import cloup
from job_scrapper import JobScrapperSkeleton
from .offers_cli_tools import request_builder, REQUEST_BUILDER_OPT, ALL_COMMON_FILTER_OPTS, make_configuration, JOB_REQUESTER
from typing import Type
from job_scrapper.cli.configure.cli_contact import ask_contact, CONTACT_OPTION


@cloup.command()
@cloup.pass_context
@click.option(
    "-u", "--url",
    help='An url to archive. Equivalent to `-c "url::==::[YOUR URL]"`',
    multiple = True,
)
@REQUEST_BUILDER_OPT
@ALL_COMMON_FILTER_OPTS
@cloup.option(
    "-r", "--reverse",
    is_flag=True,
    help="Unarchive.",
)
@cloup.option(
    "-q",  "--quiet",
    is_flag=True,
    help="Disable the confirmation prompt."
)
@CONTACT_OPTION
def archive(
        ctx,
        url: tuple[str],
        quiet,
        reverse: bool = False,
        contact: str | None = None,
        **kwargs
):
    """
    Removes offers from the main database and transfer them to the
    archive database. If you want to archive a specific offer,
    you can use
    """

    if not contact:
        contact = ask_contact(ctx.obj["workdir"])

    config = make_configuration(ctx, urls=url, **kwargs)
    JobScrapperSkeleton.get_geolocator(contact=contact)

    # ENSURE THAT URL FIELD IS REQUESTED.
    if "columns" in config:
        if "url" not in config["columns"]:
            config["columns"] = [*config["columns"], "url"]
        if "origin" not in config["columns"]:
            config["columns"] = [*config["columns"], "origin"]
    else:
        config["columns"] = list(JobScrapperSkeleton.get_table("jobs").get_columns_using_sql_name())

    first_db = "maindb"
    second_db = "archive"

    if reverse:
        first_db, second_db = second_db, first_db


    with JobScrapperSkeleton.get_sql_session(
        database_name=first_db,
        workdir=ctx.obj["workdir"]
    ) as session:
        query = request_builder(ctx, session, **kwargs)
        result = JOB_REQUESTER.execute_request(session, query)

        with JobScrapperSkeleton.get_sql_session(
                database_name=second_db,
                workdir=ctx.obj["workdir"]
        ) as archive_s:
            _archive(ctx, archive_s, session, result, quiet, reverse)

def _archive(ctx, target_session, initial_session, result, quiet, reverse):
    i = 0
    header = ""
    archived = set()
    for vals in JOB_REQUESTER.result_to_flat_file_generator(result):
        if i == 0:
            header = vals
            i += 1
            continue
        i += 1

        if not quiet:
            print()
            print("----------- Next Offer -----------")
            print(header)
            print(vals)
            print()
            if reverse:
                print("Unarchive this offer ? ")
            else:
                print("Archive this offer ? ")
            inp = input("Y / N : ")

            if inp.lower() not in ("y", "yes"):
                print("Offer NOT archived.")
                continue

        zip_header = header.split("\t")
        zip_item = vals.split("\t")


        if len(zip_item) != len(zip_header):
            ctx.obj["logger"].logger.error(
                "Unable to %s-archive this offer : can not extract url !\n%s\n%s",
                "un" if reverse else "",
                zip_header,
                zip_item,
            )

        dict_val = dict(zip(zip_header, zip_item))
        url = dict_val["url"]
        origin = dict_val["origin"]
        class_: Type[JobScrapperSkeleton] = JobScrapperSkeleton.SCRAPER_REGISTRY[origin]

        job_obj: JobScrapperSkeleton = class_.load_from_db(
            url=url,
            session=initial_session,
            use_db_init_time_stamp=True,
        )
        job_obj.archive(
            initial_session=initial_session,
            target_session=target_session,
        )

        archived.add(job_obj.url)

    print()
    if reverse:
        print(len(archived), "offers unarchived.")
    else:
        print(len(archived), "offers archived.")

    if archived:
        print()
        print("To reverse your actions :")
        r_flag = "" if reverse else "--reverse"

        for archive_url in archived:
            print("job-scrapper", "offers", "archive", r_flag, "--quiet", "--url", f'"{archive_url}"')







