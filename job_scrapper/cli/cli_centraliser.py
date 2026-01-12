from job_scrapper.cli.cli_base import cli
from job_scrapper.cli.configure.cli_groupe_configure import configure
from job_scrapper.cli.offers.offers_cli import offers
from job_scrapper.cli.standalones.scrapper_cli import scrap

cli.add_command(offers)
cli.add_command(configure)
cli.add_command(scrap, name="fetch-offers")
# cli.add_command(enumerate)