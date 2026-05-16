import main


def test_main_shows_and_activates_window(monkeypatch):
    calls = []

    class FakeApplication:
        def __init__(self, argv):
            calls.append(("app", argv))

        def exec(self):
            calls.append(("exec",))
            return 0

    class FakeWindow:
        def show(self):
            calls.append(("show",))

        def raise_(self):
            calls.append(("raise",))

        def activateWindow(self):
            calls.append(("activate",))

    monkeypatch.setattr(main, "QApplication", FakeApplication)
    monkeypatch.setattr(main, "MainWindow", FakeWindow)

    assert main.main() == 0
    assert [call[0] for call in calls[-4:]] == ["show", "raise", "activate", "exec"]
