from job_scrapper.cli.scrapper_cli import scrap
# from sql.cli.enumerate_cli import enumerate
from job_scrapper.cli.ask_contact import configure_contact
from job_scrapper.cli.cli_base import cli
from job_scrapper.sql.cli.keyword_cli import manage_keywords
from job_scrapper.sql.cli.request_offer_job_cli import request, request_format_help
from job_scrapper.sql.cli.localisation_cli import geolocalisation
from job_scrapper.cli.cli_configure import configure
from job_scrapper.cli.offers_cli import offers

###################################
#           configure             #
###################################
configure.add_command(geolocalisation, name="geolocalisation")
configure.add_command(manage_keywords, name="keywords")
configure.add_command(configure_contact, name="contact")

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