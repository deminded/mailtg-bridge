from mailtg_bridge.commands import parse_command
def test_strict_command_and_token():
    assert parse_command("MAILTG OFF secret","","secret").enabled is False
    assert parse_command("","mailtg on secret\nquoted","secret").enabled is True
    assert parse_command("MAILTG ON extra words","","secret") is None
    assert parse_command("MAILTG ON","","secret") is None
    assert parse_command("MAILTG ON token","","") is None

def test_command_survives_copied_formatting():
    # Live test: user copied "`MAILTG ON`" from a formatted instruction; the trailing
    # backtick made it unparseable. Wrappers (backticks/quotes/*bold*) must be tolerated.
    assert parse_command("","MAILTG ON`","").enabled is True
    assert parse_command("`MAILTG OFF`","","").enabled is False
    assert parse_command("","*MAILTG ON*","").enabled is True
    assert parse_command('"MAILTG ON"',"","").enabled is True
