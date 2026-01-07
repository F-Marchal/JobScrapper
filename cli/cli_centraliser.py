from job_scrapper.cli.scrapper_cli import scrap
# from sql.cli.enumerate_cli import enumerate
from cli.ask_contact import configure_contact
from cli.cli_base import cli
from sql.cli.keyword_cli import manage_keywords
from sql.cli.request_job_cli import request, request_format_help
from sql.cli.localisation_cli import geolocalisation
cli.add_command(configure_contact)
cli.add_command(manage_keywords)
cli.add_command(scrap)
cli.add_command(request_format_help)
cli.add_command(request)
cli.add_command(geolocalisation)
# cli.add_command(enumerate)