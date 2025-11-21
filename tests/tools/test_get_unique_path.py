from tests.conftest import BaseTest
from tools.get_unique_path import get_unique_path
import os

class TestGetUniquePath(BaseTest):
    """Test functions contained into tools.get_unique_path"""

    def test_get_unique_path__no_ext(self):
        """Test get_unique_path using a file name and no file extension"""
        file_folder = os.path.join(self.test_folder, "Unique")
        os.mkdir(file_folder)

        file = os.path.join(file_folder, "Alpha")
        expected = [
            "Alpha",
            *[f"Alpha-{i}" for i in range(1, 11)]
        ]
        self.tracker.screen("file path", file)
        self.tracker.screen("expected paths", expected)

        for i in range(0, 11):
            with open(get_unique_path(file), "w"):
                pass

        all_files = os.listdir(file_folder)
        self.tracker.screen("paths founds", all_files)

        assert set(all_files) == set(expected)

    def test_get_unique_path__with_same_ext(self):
        """Test get_unique_path using a file name and a file extension already present on the file"""
        file_folder = os.path.join(self.test_folder, "Unique")
        os.mkdir(file_folder)

        file = os.path.join(file_folder, "Beta")
        expected = [
            "Beta.txt",
            *[f"Beta-{i}.txt" for i in range(1, 11)]
        ]
        self.tracker.screen("file path", file)
        self.tracker.screen("expected paths", expected)

        for i in range(0, 11):
            with open(get_unique_path(file, ext=".txt"), "w"):
                pass

        all_files = os.listdir(file_folder)
        self.tracker.screen("paths founds", all_files)

        assert set(all_files) == set(expected)

    def test_get_unique_path__add_ext(self):
        """Test get_unique_path using a file name and a file extension not present on the file"""
        file_folder = os.path.join(self.test_folder, "Unique")
        os.mkdir(file_folder)

        file = os.path.join(file_folder, "Gamma")
        expected = [
            "Gamma.txt",
            *[f"Gamma-{i}.txt" for i in range(1, 11)]
        ]
        self.tracker.screen("file path", file)
        self.tracker.screen("expected paths", expected)

        for i in range(0, 11):
            with open(get_unique_path(file, ext="txt"), "w"):
                pass

        all_files = os.listdir(file_folder)
        self.tracker.screen("paths founds", all_files)

        assert set(all_files) == set(expected)
