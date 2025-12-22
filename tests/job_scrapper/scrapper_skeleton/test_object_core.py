import os

import pytest
from tests.job_scrapper.js_base_test import JobScrapperBaseTestClass

from job_scrapper.scrapper_skeleton.object_core import ScrapperObjectCore, time


class TestScrapperObjectCore(JobScrapperBaseTestClass):
    """Test ScrapperObjectCore main functionalities."""
    icl = ScrapperObjectCore

    def get_scrapper(self):
        return ScrapperObjectCore

    # --- --- --- --- Attributes managements --- --- --- ----
    @pytest.mark.parametrize(
        "input_str, expected",
        [
            ("  File\tName\nWith  Spaces  ", "File name with spaces"),
            ("project<version>v1.0*", "Projectversionv1.0"),
            ("êàéèô", "Eaeeo"),
            ("Tést\tFile\nWith\nAccénts", "Test file with accents"),
            (None, ""),
            ("---***Invalid***---", "---invalid---"),
        ],
    )
    def test_clean_string(self, input_str, expected):
        """Test the ScrapperObjectCore.clean_string methods. should be tested first
        since this method is used by almost all attributes when set."""
        self.screen_var("input", input_str)
        self.screen_var("expected", expected)

        cleaned_input = ScrapperObjectCore.clean_string(input_str)
        self.screen_var("cleaned_input", cleaned_input)

        assert cleaned_input == expected

    @pytest.mark.parametrize(
        "suffix",
        [
            ScrapperObjectCore.distance_suffix,
            ScrapperObjectCore.keyword_suffix,
            ScrapperObjectCore.time_stamp_suffix,
            ScrapperObjectCore.metadata_suffix
        ],
    )
    def test_suffixes(self, suffix):
        assert ScrapperObjectCore.clean_string(suffix, keep_suffix=True) == suffix.strip().strip("_")
        assert ScrapperObjectCore.clean_string(suffix, keep_suffix=False) == ""

    def test_initialization_and_properties_default(self):
        """
        Test minimal initialisation of a ScrapperObjectCore
        """
        soc = ScrapperObjectCore(
            "AnyString",
        )
        self.tracker.screen("SOC", soc)

        assert soc.url == "AnyString"
        assert soc.title == ""
        assert soc.localisation == ""
        assert soc.contract_type == ""
        assert soc.field == ""

        assert not soc.metadata
        assert not soc.distances
        assert ScrapperObjectCore.init_time_stamp_name in soc.time_stamps

        with pytest.raises(ValueError):
            soc.add_metadata("tmp", "Pi|pe value")

    def _generate_a_test_soc(
        self, instance_name: str = "SOC"
    ) -> tuple[ScrapperObjectCore, time.struct_time]:
        soc = ScrapperObjectCore(
            "AnyString",
            title="test offer",
            localisation="paris, france",
            contract_type="CDI",
            field=None,
        )
        now = soc.now()
        soc.add_metadata("message for*/ you", "<3")
        soc.add_metadata("your power is greater than :", "9 \t000")
        soc.add_distance_to(" pâris, france:\t" + soc.distance_suffix, 100.678)
        soc.add_time_stamps(" test tîme" + soc.time_stamp_suffix, now)
        soc.add_keyword_count("informatics*" + soc.keyword_suffix, 45)

        # Collision and default value
        soc.add_keyword_count("Strasbourg", -1)
        soc.add_distance_to("Strasbourg", -1)
        soc.add_time_stamps("Strasbourg", now)

        self.tracker.screen(instance_name, soc)

        return soc, now

    def test_initialization_and_properties_value(self):
        """
        Test most attributes manipulation that can be done
        with a  ScrapperObjectCore
        """
        soc, now = self._generate_a_test_soc()

        # Base attributes
        assert soc.url == "AnyString"
        assert soc.title == "Test offer"
        assert soc.localisation == "Paris, France"
        assert soc.contract_type == "CDI"
        assert soc.field == ""

        # Metadat exist
        # If assert True : Text is correctly cleaned.
        assert soc.metadata_exist("message for*/ you" + soc.metadata_suffix)
        assert soc.metadata_exist("Message for you")
        assert soc.distance_to_exist("pâris, france:\t" + soc.distance_suffix)
        assert soc.distance_to_exist("Paris, france")
        assert soc.time_stamps_exist(" test tîme" + soc.time_stamp_suffix)
        assert soc.time_stamps_exist("Test time")
        assert soc.keyword_exist("informatics*" + soc.keyword_suffix)
        assert soc.keyword_exist("Informatics")

        # Metadata content
        # If assert True : Text is correctly cleaned and value is correct !
        assert soc.metadata["Message for you"] == "<3"
        assert soc.retrieve_metadata("message for*/ you") == "<3"
        assert soc.metadata["Your power is greater than"] == "9_000"

        assert soc.distances["Paris, france"] == 100.678
        assert (
            soc.retrieve_distance_to("pâris, france:\t" + soc.distance_suffix)
            == 100.678
        )

        assert soc.time_stamps["Test time"] == now
        assert (
            soc.retrieve_time_stamps(" test tîme" + soc.time_stamp_suffix)
            == now
        )
        assert ScrapperObjectCore.init_time_stamp_name in soc.time_stamps

        assert soc.keywords["Informatics"] == 45
        assert (
            soc.retrieve_keyword_count("informatics*" + soc.keyword_suffix)
            == 45
        )

        # Metadata exist default_value_do_not_count
        assert not soc.distance_to_exist(
            "Strasbourg", default_value_do_not_count=True
        )
        assert soc.distance_to_exist(
            "Strasbourg", default_value_do_not_count=False
        )
        assert not soc.keyword_exist(
            "Strasbourg", default_value_do_not_count=True
        )
        assert soc.keyword_exist("Strasbourg", default_value_do_not_count=False)

    def test_full_empty_edge_case(self):
        soc = ScrapperObjectCore("")
        soc.add_keyword_count("", 5)
        soc.add_distance_to("", 5)
        soc.add_time_stamps("", soc.now())
        soc.add_metadata("", "")
        self.screen_var("soc", soc)

        assert soc.url == ""
        assert soc.title == ""
        assert soc.localisation == ""
        assert soc.contract_type == ""
        assert soc.field == ""
        assert soc.metadata_exist("")
        assert soc.distance_to_exist("")
        assert soc.keyword_exist("")
        assert soc.time_stamps_exist("")

    def test_remove_value_from_dict(self):
        """Test remove_[dict name] methods.
        Uses uncleaned string to test those methods."""
        soc, _ = self._generate_a_test_soc()

        assert soc.metadata_exist("Message for you")
        assert soc.time_stamps_exist("Test time")
        assert soc.distance_to_exist("Paris, france")
        assert soc.keyword_exist("Informatics")

        soc.remove_metadata("message for*/ you")
        soc.remove_time_stamps(" test tîme")
        soc.remove_distance_to(" pâris, france:\t")
        soc.remove_keyword_count("informatics*")

        assert not soc.metadata_exist("Message for you")
        assert not soc.time_stamps_exist("Test time")
        assert not soc.distance_to_exist("Paris, france")
        assert not soc.keyword_exist("Informatics")

    # --- --- --- --- Attributes managements --- --- --- ----
    # --- --- --- --- Exports managements --- --- --- ----
    def test_to_dict(self):
        """Test ScrapperObjectCore.to_dict() method"""
        soc, now = self._generate_a_test_soc()
        dict_ = soc.to_dict()
        self.tracker.screen("soc_to_dic", dict_)

        assert dict_["#Time_Stamp"] == soc.strftime(now)
        assert dict_["Origin"] == soc.get_standardised_class_name()
        assert dict_["Localisation"] == soc.localisation
        assert dict_["Field"] == soc.field
        assert dict_["Contract"] == soc.contract_type
        assert dict_["Title"] == soc.title
        assert dict_["Url"] == soc.url

        assert (
            dict_["Metadata"]
            == "Message for you=<3|Your power is greater than=9_000"
        )
        assert dict_["Paris, france" + soc.distance_suffix] == 100.678
        assert dict_["Informatics" + soc.keyword_suffix] == 45

        assert (
            not ScrapperObjectCore.init_time_stamp_name + soc.time_stamp_suffix
            in dict_
        )
        assert dict_["Test time" + soc.time_stamp_suffix] == soc.strftime(now)

    def test_init_time_stamp_name_variable(self):
        """Ensure that init_time_stamp_name respect  ScrapperObjectCore.clean_string.
        If this is not respected, to_dict() and time_stamps_exist can fail miserably.
        """
        string = ScrapperObjectCore.init_time_stamp_name
        assert string == ScrapperObjectCore.clean_string(string)

    def test_default_header_column_names(self):
        distance_suffix = ScrapperObjectCore.distance_suffix
        keyword_suffix = ScrapperObjectCore.keyword_suffix
        time_stamp_suffix = ScrapperObjectCore.time_stamp_suffix

        for values in ScrapperObjectCore.default_header:
            assert values == values.removesuffix(distance_suffix)
            assert values == values.removesuffix(keyword_suffix)
            assert values == values.removesuffix(time_stamp_suffix)

    def test_get_unique_name(self):
        """Test ScrapperObjectCore.get_unique_path with file and folder"""
        # Folder test
        for i in range(0, 11):
            test_dir_path = ScrapperObjectCore.get_unique_path("./testdir", "")
            self.tracker.screen(f"test_dir_path_{i}", test_dir_path)
            assert not os.path.exists(test_dir_path)
            os.mkdir(test_dir_path)

        # File test
        for i in range(0, 11):
            test_file_path = ScrapperObjectCore.get_unique_path(
                "./testdir", ".txt"
            )
            self.tracker.screen(f"test_file_path{i}", test_file_path)
            assert not os.path.exists(test_file_path)
            with open(test_file_path, "w", encoding="UTF-8"):
                pass

    def test_flat_unflat(self):
        """Test ScrapperObjectCore.unflat method."""
        soc, _ = self._generate_a_test_soc()
        flat_soc = soc.flat()
        header, line, *_ = flat_soc.split("\n")
        self.tracker.screen("header", header)
        self.tracker.screen("line", line)

        unflat = soc.unflat(header, line)
        self.tracker.screen("unflat", unflat)

        flat_unflat = soc.flat()
        self.tracker.screen("flat_unflat", flat_unflat)

        assert unflat.to_dict() == soc.to_dict()
        assert flat_unflat == flat_soc

    def test_flat_unflat_edge_case(self):
        soc = ScrapperObjectCore("")
        soc.add_keyword_count("", 5)
        soc.add_distance_to("", 5)
        soc.add_time_stamps("", soc.now())
        soc.add_metadata("", "")
        soc.add_metadata("o", "b")
        self.screen_var("soc3", soc)

        flat_soc = soc.flat()
        header, line, *_ = flat_soc.split("\n")
        self.tracker.screen("header", header)
        self.tracker.screen("line", line)

        unflat = soc.unflat(header, line)
        self.tracker.screen("unflat", unflat)

        flat_unflat = soc.flat()
        self.tracker.screen("flat_unflat", flat_unflat)

        assert unflat.to_dict() == soc.to_dict()
        assert flat_unflat == flat_soc


    def test_export_import_to_flat_file_and_equality(self):
        """Test ScrapperObjectCore.get_unique_path with file and folder"""

        soc1_a, _ = self._generate_a_test_soc(instance_name="SOC1-A")
        soc2_a, _ = self._generate_a_test_soc(instance_name="SOC2-A")
        soc1_a.url = "soc1"
        soc2_a.url = "soc2"

        soc3_a = ScrapperObjectCore("")
        soc3_a.add_keyword_count("", 5)
        soc3_a.add_distance_to("", 5)
        soc3_a.add_time_stamps("", soc3_a.now())
        soc3_a.add_metadata("", "")
        soc3_a.add_metadata("o", "b")
        self.screen_var("SOC3-A", soc3_a)

        self.tracker.re_screen_all()

        ScrapperObjectCore.batch_export_to_flat_file([soc3_a, soc1_a, soc2_a], None)

        result = list(ScrapperObjectCore.import_from_flat_file())

        assert len(result) == 3

        soc1_b = result[1]
        soc2_b = result[2]
        soc3_b = result[0]

        self.tracker.write("\n")
        self.re_screen_var("SOC1-A")
        self.tracker.screen("SOC1-B", soc1_b)
        self.tracker.write("\n")
        self.re_screen_var("SOC2-A")
        self.tracker.screen("SOC2-B", soc2_b)
        self.tracker.write("\n")
        self.re_screen_var("SOC3-A")
        self.tracker.screen("SOC3-B", soc3_b)

        assert soc3_a.flat() == soc3_b.flat()
        assert soc3_b == soc3_a
        assert soc1_b == soc1_a
        assert soc2_b == soc2_a

    # --- --- --- --- Exports managements --- --- --- ----
