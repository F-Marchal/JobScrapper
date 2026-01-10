import click


def main():
    click.echo("main() was called")
    raise ValueError("BOOM")

if __name__ == "__main__":
    main()
