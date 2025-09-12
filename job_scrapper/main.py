import logging

import click
import cloup

from .scrapper_skeleton import scrapper_skeleton as skl


@cloup.group()
@cloup.option(
    "-v",
    "--verbosity",
    type=click.Choice(
        list(skl.JobScrapperSkeleton.logger_levels), case_sensitive=False
    ),
    default="INFO",
    help="Niveau de logs",
)
@cloup.pass_context
def cli(ctx, verbosity):
    """Main Command line Interface. Will be specialised later on."""
    skl.JobScrapperSkeleton.set_logging_level(verbosity)
    ctx.obj = {"verbosity": verbosity}


# --- --- --- SCRAP group --- --- ---
@cli.group()
@cloup.option(
    "-v",
    "--verbosity",
    type=click.Choice(
        list(skl.JobScrapperSkeleton.logger_levels), case_sensitive=False
    ),
    default="INFO",
    help="Niveau de logs",
)
@cloup.pass_context
def scrap(ctx):
    """Commandes liées au scraping."""
    pass


@scrap.command()
@cloup.pass_obj
def sanofi(obj):
    """Scrap sanofi website for job offers."""
    logging.info(f"Scraping en mode A (verbosity={obj['verbosity']})")


@scrap.command()
@cloup.pass_obj
def b(obj):
    """Scrap en mode B (complet)."""
    logging.info(f"Scraping en mode B (verbosity={obj['verbosity']})")


'''
# --- Groupe secondaire AGGREGATE ---
@cli.group()
@cloup.pass_context
def aggregate(ctx):
    """Commandes liées à l'agrégation."""
    pass


@aggregate.command()
@cloup.pass_obj
def daily(obj):
    """Agrégation journalière."""
    logging.info(f"Agrégation journalière (verbosity={obj['verbosity']})")

'''
if __name__ == "__main__":
    cli()
