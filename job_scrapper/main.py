#!/usr/bin/python3
from job_scrapper.cli.cli_centraliser import cli
import io
import click
import traceback

def main():
    ctx_obj = {}
    try:
        cli(standalone_mode=False, obj=ctx_obj)
    except click.ClickException as e:
        # Capture output in a string
        e.show()
        with io.StringIO() as buf:
            e.show(file=buf)  # redirect Click's show() to a buffer
            output = buf.getvalue()

        # Store in logfile
        if "log_file" in ctx_obj:
            ctx_obj["logger"].logger.debug(
                output
            )
        raise SystemExit(e.exit_code)

    except Exception as e:
        # Display a less ugly error message
        ctx_obj["logger"].logger.critical(traceback.format_exc())
        if ctx_obj["log_file"]:
            msg = f" Note that all debugs logs are stored in '{ctx_obj['log_file']}'."
        else:
            msg = ""
        ctx_obj["logger"].logger.critical(
            "An unexpected error occurred during execution.%s See Above traceback for more details.\n%s : \t%s",
            msg,
            e.__class__.__name__, e,

        )
        raise SystemExit(1)


if __name__ == "__main__":
    main()
