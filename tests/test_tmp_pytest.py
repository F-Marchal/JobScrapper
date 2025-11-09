from tests.conftest import BaseTest

class TestAlwaysFail(BaseTest):
    def test_upload_artefact(self):
        self.screen_var("Alpha","Beta")
        self.icl.logger.debug("TMP")
        assert False