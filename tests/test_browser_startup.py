import services.browser as browser_module
from services.browser import Browser


class FakeCamoufox:
    attempts = 0

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.exited = False

    def start(self):
        self.__class__.attempts += 1
        if self.attempts < 3:
            raise ValueError(
                'No WebGL data found for vendor "ATI Technologies Inc." '
                'and renderer "Radeon HD 3200 Graphics, or similar"'
            )
        return object()

    def __exit__(self, *args):
        self.exited = True


def test_restart_resamples_invalid_webgl_preset(monkeypatch):
    FakeCamoufox.attempts = 0
    monkeypatch.setattr(browser_module, "Camoufox", FakeCamoufox)
    monkeypatch.setattr(Browser, "_setup_context", lambda self: None)

    browser = Browser()

    assert FakeCamoufox.attempts == 3
    assert browser.browser is not None


def test_restart_does_not_hide_other_value_errors(monkeypatch):
    class InvalidConfigCamoufox(FakeCamoufox):
        def start(self):
            raise ValueError("Invalid browser configuration")

    monkeypatch.setattr(browser_module, "Camoufox", InvalidConfigCamoufox)

    try:
        Browser()
    except ValueError as error:
        assert str(error) == "Invalid browser configuration"
    else:
        raise AssertionError("unrelated startup errors must not be retried")
