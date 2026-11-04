import random

import pytest

from atomicworld import bigbang
from atomicworld.repository import ParticleCatalog

CATALOG = ParticleCatalog()


def test_generate_bits_length_and_alphabet():
    bits = bigbang.generate_bits(100, random.Random(42))
    assert len(bits) == 100 and set(bits) <= {"0", "1"}


def test_generate_is_reproducible_with_seed():
    assert bigbang.generate_bits(64, random.Random(1)) == bigbang.generate_bits(64, random.Random(1))


def test_timed_returns_one_duration_per_bit():
    bits, durations = bigbang.generate_bits_timed(20)
    assert len(bits) == len(durations) == 20


def test_transforms():
    assert bigbang.invert("0011") == "1100"
    assert bigbang.reverse("0011") == "1100"
    assert bigbang.invert_and_reverse("0001") == "0111"


def test_zero_bits_rejected():
    with pytest.raises(ValueError):
        bigbang.generate_bits(0)


def test_match_repeated_bytes_each_once():
    # 'Up' (00000000) dos veces seguidas + 3 bits sobrantes
    result = bigbang.match_particles("00000000" "00000000" "101", CATALOG)
    assert [p.name for p in result.found] == ["Up", "Up"]
    assert result.full_bytes == 2 and result.leftover_bits == 3
    assert result.matches[-1].particle is None
