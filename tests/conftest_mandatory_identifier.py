from tests.conftest import BaseTest
import pytest

@pytest.mark.mandatory_user_agent
class MandatoryIdentifierTestClass(BaseTest):
    @pytest.fixture(autouse=True)
    # pylint: disable=W0201
    def _user_agent(self, request):
        self.user_agent = request.config.getoption("--user-agent")
        if not self.user_agent:
            raise RuntimeError(
                f"{type(self).__name__} need a valid user agent (--user-agent). "
                f"Please use --user-agent <your-email>"
            )
