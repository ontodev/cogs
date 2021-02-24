import importlib.util


def test_modules():
    """Test that modules are properly loaded."""
    for module in [
        "add",
        "apply",
        "clear",
        "connect",
        "delete",
        "diff",
        "exceptions",
        "fetch",
        "helpers",
        "init",
        "ls",
        "mv",
        "merge",
        "push",
        "rm",
        "share",
        "status",
    ]:
        spec = importlib.util.find_spec("cogs." + module)
        if not spec:
            raise Exception(f"cogs.{module} does not exist")
