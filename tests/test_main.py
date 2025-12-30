import importlib
import sys


def _load_main(monkeypatch, tmp_path):
    monkeypatch.setenv("ARP_AUTH_PROFILE", "dev-insecure")
    monkeypatch.setenv("JARVIS_NODE_REGISTRY_SEED", "false")
    monkeypatch.setenv(
        "JARVIS_NODE_REGISTRY_DB_URL", f"sqlite:///{tmp_path}/node_registry.sqlite"
    )

    import jarvis_node_registry.app as app_module
    import jarvis_node_registry.__main__ as main_module

    importlib.reload(app_module)
    return importlib.reload(main_module)


def test_main_runs_uvicorn_reload(monkeypatch, tmp_path) -> None:
    main_module = _load_main(monkeypatch, tmp_path)
    calls = []

    def fake_run(*args, **kwargs):
        calls.append((args, kwargs))

    monkeypatch.setattr(main_module.uvicorn, "run", fake_run)
    monkeypatch.setattr(sys, "argv", ["prog", "--reload"])

    main_module.main()

    assert calls
    args, kwargs = calls[0]
    assert args[0] == "jarvis_node_registry.app:app"
    assert kwargs["reload"] is True


def test_main_runs_uvicorn_no_reload(monkeypatch, tmp_path) -> None:
    main_module = _load_main(monkeypatch, tmp_path)
    calls = []
    app = object()

    def fake_run(*args, **kwargs):
        calls.append((args, kwargs))

    monkeypatch.setattr(main_module.uvicorn, "run", fake_run)
    monkeypatch.setattr(main_module, "create_app", lambda: app)
    monkeypatch.setattr(sys, "argv", ["prog"])

    main_module.main()

    assert calls
    args, kwargs = calls[0]
    assert args[0] is app
    assert kwargs["reload"] is False
