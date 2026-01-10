from sqlalchemy import ColumnElement, and_
from typing import Callable
# pylint: disable=E0611
from sqlalchemy.orm import Query, Session
from sqlalchemy.sql import operators as ope

from sql.filters.filter_generator import FilterGenerator
from sql.tables import Distances, Jobs, Keywords, Metadata, TimeStamps, Places

from .sql_request_wrapper import SQLRequestWrapper


class JobRequest(SQLRequestWrapper):
    """
    Build a huge Query object to request all information related to a job in Jobs (JobExtraBase, Jobs and Distances)
    """
    def __init__(
        self,
        *args,
        place_name_normaliser: Callable[
            [str], str
        ] = Places.format_localisation,
        **kwargs,
    ):
        """
        :param place_name_normaliser: A command to normalise places names such as Places.format_localisation.
        :param args: see SQLRequestWrapper.__init__
        :param kwargs: see SQLRequestWrapper.__init__
        """
        super().__init__(*args, **kwargs)
        self.place_name_normaliser = place_name_normaliser

    # --- --- Request --- ---
    # pylint: disable=R0913,R0917,R0914
    # This is a massive overhaul method used as user interface,
    # having many arguments / positional arguments and many local variables is kind of expected
    def build_request(
        self,
        session: Session,
        columns: list[str] | None = None,
        distances_from: list[str] | None = None,
        keywords: list[str] | None = None,
        metadata: list[str] | None = None,
        time_stamps: list[str] | None = None,
        order_by: list[str] | None = None,
    ) -> Query | None:
        """
        Returns A query object that apply all filters defines in the parameters of this method.

        For distances_from, keywords, metadata, time_stamp each string of the list[str], the format expected is the
        one used by FilterParts.  See FiltersParts.format_help.

        :param session: An opened session on a database.
        :param columns: List of column to keep / filter from Jobs table
        :param distances_from: Filter / display distances from a place contained in Distances.reference_localisation
        :param keywords: Filter / display occurrences of Keywords.keyword contained inside an offer
        :param metadata: Filter / display metadata values attached to a Metadata.key attached to job offers.
        :param time_stamps: Filter / display TimeStamps values attached to a Metadata.key attached to job offers.
        :param order_by: A list of column name (form Tables or generated during the request) that should order
            the result.
        """

        # Small security to ensure correct suffixes setup
        mandatory_suffixes = {
            "time_stamp",
            "metadata",
            "keyword",
            "distance",
        }
        if not mandatory_suffixes.issubset(set(self.suffixes)):
            raise KeyError(
                "Missing suffixes in self.suffixes"
                f"\nself={self}"
                f"\nself.suffixes{self.suffixes}"
                f"\nexpected={mandatory_suffixes}"
            )

        if not columns:
            columns = list(Jobs.get_columns_using_sql_name())

        # Parse inputs
        job_filter = self.build_jobs_filter_generator(columns)
        distance_filter = self.build_distance_filter_generator(session, distances_from)
        keywords_filter = self.build_keywords_filter_generator(keywords)
        time_filter = self.build_time_stamp_filter_generator(time_stamps)
        metadata_filter = self.build_metadata_filter_generator(metadata)

        all_cols: list[ColumnElement] = [
            *job_filter.columns,
            *distance_filter.columns,
            *keywords_filter.columns,
            *time_filter.columns,
            *metadata_filter.columns,
        ]

        order_by_cols = self.build_request_order_by(all_cols, order_by)

        if not order_by_cols:
            # Avoid sqlalchemy.exc.InvalidRequestError:
            # Query contains no columns with which to SELECT from.
            return None

        query = (
            session.query(*order_by_cols)
            .join(Jobs.places_entry) # Replace .outerjoin(Distances, Distances.job_localisation == Jobs.localisation))
            .outerjoin(Keywords, ope.eq(Keywords.url, Jobs.url))
            .outerjoin(TimeStamps, ope.eq(TimeStamps.url, Jobs.url))
            .outerjoin(Metadata, ope.eq(Metadata.url, Jobs.url))
            .where(job_filter.safe_filters)
            .group_by(Jobs.url)
            .having(
                and_(
                    distance_filter.safe_filters,
                    keywords_filter.safe_filters,
                    time_filter.safe_filters,
                    metadata_filter.safe_filters,
                )
            )
            .order_by(*order_by_cols)
        )
        return query

    def build_request_order_by(
        self,
        all_cols: list[ColumnElement],
        order_by: list[str] | None = None,
    ) -> list[ColumnElement]:
        """
        Generate a list of columns ordered using <order_by>. This list can be used inside the .order_by statement.
        At the same time <all_cols> is reordered to place columned named inside <order_by> at the beginig of <all_cols>
        :param  list[ColumnElement] all_cols: A list of ColumElement to order
        :param list[str] | None order_by:  A list of ColumnElement's names.
        :return list[ColumnElement]: A list of ColumnElements ordered using column names inside <all_cols>.
        """
        if order_by is None:
            return all_cols[:]

        order = {
            self.column_name_normaliser(col_n): i
            for i, col_n in enumerate(order_by)
        }

        return sorted(
            all_cols,
            key=lambda col: order.get(
                self.column_name_normaliser(col.name), len(order)
            ),
        )

    def build_jobs_filter_generator(self, columns: list[str] | None):
        """
        Build a FilterGenerator for the Jobs table from a list of string compatible with FilterParts.
        If <columns> is None, All columns will be selected with no filters.
        """
        return self.quick_filter_generator(
            table=Jobs,
            columns=columns,
            fill_none_columns=True,
            column_creator=None,
            cast_constraint=[str]
        )

    def build_distance_filter_generator(
        self,
        session: Session,
        distances_from: list[str] | None = None,
    ) -> FilterGenerator:
        """
        Build a FilterGenerator for the Distances table from a list of string compatible with FilterParts.
        The column name used inside the strings should be an item in Distances.reference_localisation
        """


        return self.quick_filter_generator(
            table=Distances,
            columns=distances_from,
            cast_constraint=[float], # Ensure that all value used by filter are float.
            column_creator=lambda col_name: self.distance_column_command_generator(
                session=session,
                col_name=col_name,
                suffix_name="distance"
            )
        )

    def distance_column_command_generator(
            self,
            session: Session,
            col_name: str,
            suffix_name: str
    ) -> ColumnElement:
        """
        Generate a new column like object that compute the distances
        between two places.
        :param session: A session connected to the requested database
        :param col_name: The name of the column passed by the user
        :param suffix_name: The suffix to add at the end of the colun name
        :return: ColumnElement
        """
        selected_suffix = self.get_suffix(suffix_name)
        col_name = self.place_name_normaliser(col_name)
        place_column = Places.get_job_place(session, col_name)

        if not place_column:
            raise KeyError(f"Unable to find a place named '{col_name}' in database.")

        if not place_column.is_computable():
            raise KeyError(
                f"Although the database contains a place named '%s', the coordinate"
                f"of this place can not be used : %s".format(col_name, place_column.to_dict())
            )

        return place_column.get_column_distance_to_self(col_name.removesuffix(selected_suffix) + selected_suffix)


    # def build_distance_filter_generator(
    #     self,
    #     distances_from: list[str] | None = None,
    # ) -> FilterGenerator:
    #     """
    #     Build a FilterGenerator for the Distances table from a list of string compatible with FilterParts.
    #     The column name used inside the strings should be an item in Distances.reference_localisation
    #     """
    #     return self.quick_filter_generator(
    #         table=Distances,
    #         columns=distances_from,
    #         cast_constraint=[float], # Ensure that all value used by filter are float.
    #         column_creator=self.quick_column_creator(
    #             label_col=Distances.reference_localisation,
    #             value_col=Distances.distance,
    #             suffix_name="distance",
    #             else_value=None,
    #         ),
    #     )

    def build_keywords_filter_generator(
        self,
        keywords: list[str] | None = None,
    ):
        """
        Build a FilterGenerator for the Keywords table from a list of string compatible with FilterParts.
        The column name used inside the strings should be an item in Keywords.keyword
        """
        return self.quick_filter_generator(
            table=Keywords,
            columns=keywords,
            cast_constraint=[int], # Ensure that all value used by filter are integers.
            column_creator=self.quick_column_creator(
                label_col=Keywords.keyword,
                value_col=Keywords.occurrence,
                suffix_name="keyword",
                else_value=None,
            ),
        )

    def build_time_stamp_filter_generator(
        self,
        time_stamps: list[str] | None = None,
    ) -> FilterGenerator:
        """
        Build a FilterGenerator for the TimeStamps table from a list of string compatible with FilterParts.
        The column name used inside the strings should be an item in TimeStamps.label
        """
        return self.quick_filter_generator(
            table=TimeStamps,
            columns=time_stamps,
            cast_constraint=[FilterGenerator.FilterPart.date_cast_function],
            column_creator=self.quick_column_creator(
                label_col=TimeStamps.label,
                value_col=TimeStamps.time_stamp,
                suffix_name="time_stamp",
                else_value=None,
            ),
        )

    def build_metadata_filter_generator(
        self, metadata: list[str] | None = None
    ) -> FilterGenerator:
        """
        Build a FilterGenerator for the Metadata table from a list of string compatible with FilterParts.
        The column name used inside the strings should be an item in Metadata.key
        """
        return self.quick_filter_generator(
            table=Metadata,
            columns=metadata,
            cast_constraint=[str],
            column_creator=self.quick_column_creator(
                label_col=Metadata.key,
                value_col=Metadata.value,
                suffix_name="metadata",
                else_value=None,
            ),
        )
