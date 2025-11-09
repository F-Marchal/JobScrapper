from job_scrapper.cli.scrapper_cli import scrap
from job_scrapper.cli.database_cli import database
from cli.cli_base import cli

cli.add_command(scrap)
cli.add_command(database)