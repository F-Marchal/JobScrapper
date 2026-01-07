import click
import cloup
from job_scrapper.scrapper_skeleton.scrapper_skeleton import JobScrapperSkeleton
from sql.tables import Places, Distances
from sqlalchemy import or_
from cli.ask_contact import CONTACT_OPTION, ask_contact
from tools.geolocalisation import Geolocalisation


@cloup.group()
def geolocalisation():
    """Add, modify, consult localization coordinate (decimal degree) in database."""

@geolocalisation.command()
@click.pass_context
def diagnosis(ctx):
    """Run a diagnosis to detect unknown localization."""
    with JobScrapperSkeleton.get_sql_session(workdir=ctx.obj["workdir"]) as session:
        places = session.query(Places).where(
            or_(
                Places.longitude.is_(None),
                Places.latitude.is_(None),
            )
        ).all()
        print()
        print(f"{len(places)} with invalid coordinates found :")
        print("LOCATION\tLATITUDE\tLONGITUDE")
        for p in places:
            print(f"{p.localisation} {p.latitude} {p.longitude}")

@geolocalisation.command()
@click.pass_context
@CONTACT_OPTION
@cloup.argument(
    "place",
    type=str,
    help="A place to know its coordinates ",
)
@cloup.option(
    "-s", "--country-code",
    type=str,
    help="A country code to restrain coordinate (e.g. FR, EU, RU...). "
         "(ISO 3166-1 alpha-2 country codes)",
    default=None,
)

def geolocate(ctx, place, contact, country_code):
    """Geolocate a place using geopy. (decimal degree coordinate)"""
    if not contact:
        contact = ask_contact(ctx.obj["workdir"])
    geolocator = JobScrapperSkeleton.get_geolocator(contact=contact)

    with JobScrapperSkeleton.get_sql_session(workdir=ctx.obj["workdir"]) as session:
        lat, long = geolocator.geolocate(
            session,
            place,
            lazy=False,
            add_in_database=False,
            restrict_country_codes=[country_code],
        )

        print("LOCATION\tLATITUDE\tLONGITUDE")
        print(f"{place}\t{lat}\t{long}")

    print()
    print(f"Do you want to add '{place}' in database ?")
    valid = input("Y / N : ")
    if valid.lower() in ("y", "yes"):
        add_place_to_db(ctx, place, lat, long)

@geolocalisation.command()
@click.pass_context
@cloup.argument(
    "place",
    type=str,
    help="A list of place to know their coordinates from database. If unfill, all"
         "places are used",
    nargs=-1,
    default=tuple(),
)
def extract(ctx, place):
    """Extract places from database and display theirs longitude and latitude (decimal degree).
    None --> Unknown longitude / latitude.
    "-" --> Place not in database."""


    with JobScrapperSkeleton.get_sql_session(workdir=ctx.obj["workdir"]) as session:
        if not place:
            result = session.query(Places).all()
        else:
            result = session.query(Places).where(Places.localisation.in_(place)).all()

        print()
        print("LOCATION\tLATITUDE\tLONGITUDE")
        missing = set(place)
        for l in sorted(result, key=lambda x: x.localisation):
            print(f"{l.localisation}\t{l.lat}\t{l.long}")
            if l.localisation in missing:
                missing.remove(l.localisation)

        for place in missing:
            print(f"{place}\t-\t-")

@geolocalisation.command()
@click.pass_context
@cloup.argument(
    "place",
    type=str,
    help="A place to set its coordinates",
)
@cloup.argument(
    "latitude",
    type=float,
    help="Place's latitude (decimal degree)",
)
@cloup.argument(
    "longitude",
    type=float,
    help="Place's longitude (decimal degree)",
)

def write(ctx, place, latitude, longitude):
    """Write coordinate (decimal degree) to database."""
    add_place_to_db(ctx, place, latitude, longitude)

    print("Done.")

def add_place_to_db(ctx, place, latitude, longitude):
    with JobScrapperSkeleton.get_sql_session(workdir=ctx.obj["workdir"]) as session:
        session.add(
            Places(
                latitude=latitude,
                longitude=longitude,
                localisation=place,
            )
        )



@geolocalisation.command()
@click.pass_context
@cloup.argument(
    "reference_places",
    type=str,
    help="A list of place to compute distance from.",
    nargs=-1,
)
@cloup.option(
    "-e",
    "--export",
    is_flag=True,
    help="Export all coordinate in the database. Be warn that this can lead to very huge database"
         "since this will add nb_ref * nb_place entry in the database (nb_ref=number of places gave"
         "to this command ; nb_place=number of places in database.)",
)
@cloup.option(
    "-f",
    "--force-recompute",
    is_flag=True,
    help="By default, distances known in the database are not compute again. Use this"
         "flag to force recomputation.",
)
def compute_distances_to(
        ctx,
        reference_places: list[str],
        force_recompute: bool,
        export: bool
):
    """Compute distances between a set a places and all other places in database."""
    with JobScrapperSkeleton.get_sql_session(workdir=ctx.obj["workdir"]) as session:
        all_places = session.query(Places.localisation).distinct().all()

        for ref in reference_places:
            print()
            ref_entry = Geolocalisation.get_localisation_from_database(session, ref)
            if ref_entry is None:
                print(
                    f"Distance to '{ref}' can not be computed since "
                    f"'{ref}' coordinate are unknown. (NOT IN DATABASE)"
                )
                print(f"Please use `geolocalisation geolocate {ref}` to fix it.")
                continue
            elif not ref_entry.is_computable():
                print(
                    f"Distance to '{ref}' can not be computed since "
                    f"'{ref}' coordinate are unknown. (INVALID COORDINATE IN DATABASE)"
                )
                print(f"Please use `geolocalisation write {ref} [latitude] [longitude]` to fix it.")
                continue


            print(f"Distances to '{ref}' :")
            print("LOCATION\tDISTANCE_KM")
            for place in all_places:
                distance = Geolocalisation.compute_distance(
                    session=session,
                    reference_localisation=ref,
                    second_localisation=place[0],
                    lazy=not force_recompute,
                    add_in_database=export,
                )
                if isinstance(distance, float):
                    distance = round(distance, 3)

                print(f"{place[0]}\t{distance}")

@geolocalisation.command()
@click.pass_context
@cloup.argument(
    "reference_places",
    type=str,
    help="A list of places for which the previously computed distances must be removed.",
    nargs=-1,
)
def remove_distances_to(ctx, reference_places):
    """Remove previously computed distances from database."""
    with JobScrapperSkeleton.get_sql_session(workdir=ctx.obj["workdir"]) as session:
        for ref in reference_places:
            all_associated_entry = session.query(Distances).where(Distances.reference_localisation == ref).all()

            if not all_associated_entry:
                print(f"No entry to delete for '{ref}'.")
                continue

            length = len(all_associated_entry)

            for entry in all_associated_entry:
                session.delete(entry)
            print(f"All {length} Distance entry attached to '{ref}' deleted.")