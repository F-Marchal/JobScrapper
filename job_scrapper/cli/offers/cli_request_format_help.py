import cloup
from .offers_cli_tools import JOB_REQUESTER

@cloup.command()
def request_format_help():
    """How to format columns that you are requesting."""
    print(JOB_REQUESTER.get_string_format_help())
