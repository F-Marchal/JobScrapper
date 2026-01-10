from job_scrapper.cli.standalones.scrapper_cli import scrap

from job_scrapper.cli.cli_base import cli

from job_scrapper.cli.standalones.request_offer_job_cli import request, request_format_help

from job_scrapper.cli.configure.cli_groupe_configure import configure
from job_scrapper.cli.offers.offers_cli import offers



###################################
#              offers             #
###################################
offers.add_command(request, name="list")
offers.add_command(request_format_help, name="column-format-help")

###################################
#              cli             #
###################################
cli.add_command(scrap, name="fetch-offers")
cli.add_command(offers)
cli.add_command(configure)

# cli.add_command(enumerate)