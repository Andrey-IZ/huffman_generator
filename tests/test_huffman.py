import pytest
import random
import string
from huffman import huffman_decode, huffman_encode, Counter


@pytest.mark.parametrize("n",[i for i in range(20, 100, 10)])
def test_huffman_randomly(n):
    for _ in range(n):
        length = random.randint(0, 32)
        s = "".join(random.choice(string.ascii_letters) for _ in range(length))
        print(s)
        code = huffman_encode(Counter(s))
        encoded = "".join(code[ch] for ch in s)
        assert huffman_decode(encoded, code) == s


@pytest.mark.parametrize("input_string", ["", " ", "   ", "kck92sa!@", "щоь)32уЛаоряюйСЩы"])
def test_huffman(input_string):
    code = huffman_encode(Counter(input_string))
    encoded = "".join(code[ch] for ch in input_string)
    assert huffman_decode(encoded, code) == input_string
