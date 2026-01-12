import cloup
from .cli_contact import configure_contact
from .cli_keyword import manage_keywords
from .cli_localisation import geolocalisation

@cloup.group()
def configure():
    """Configuration and management of different aspect of this application such
    as keywords searched inside offers, geolocalisation of offers and
    contact information."""
    pass

configure.add_command(geolocalisation, name="geolocalisation")
configure.add_command(manage_keywords, name="keywords")
configure.add_command(configure_contact, name="contact")