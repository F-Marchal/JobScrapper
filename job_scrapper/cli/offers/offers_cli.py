from .cli_list import request
from .cli_request_format_help import request_format_help
from .cli_archive import archive
import cloup

@cloup.group()
@cloup.pass_context
def offers(ctx):
    pass



offers.add_command(request, name="list")
offers.add_command(request_format_help, name="column-format-help")
offers.add_command(archive, name="archive")