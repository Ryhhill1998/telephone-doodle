"""Room codes: four letters, none of them ambiguous."""

from rooms.codes import ALPHABET, CODE_LENGTH, generate_code


def test_codes_are_the_right_length_and_alphabet() -> None:
    code = generate_code()

    assert len(code) == CODE_LENGTH
    assert all(letter in ALPHABET for letter in code)


def test_the_alphabet_excludes_ambiguous_letters() -> None:
    assert "I" not in ALPHABET
    assert "O" not in ALPHABET


def test_codes_are_not_all_the_same() -> None:
    """Not a uniqueness proof -- just a sign `generate_code` isn't constant."""
    codes = {generate_code() for _ in range(50)}
    assert len(codes) > 1
