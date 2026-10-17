import unittest

from wordfreq.counter import count_words


class CountWordsTest(unittest.TestCase):
    def test_counts_and_orders_by_count(self):
        self.assertEqual(count_words("b a b"), [("b", 2), ("a", 1)])

    def test_equal_counts_sort_by_word(self):
        self.assertEqual(count_words("pear apple"), [("apple", 1), ("pear", 1)])

    def test_ignores_case_and_punctuation(self):
        self.assertEqual(count_words("Tea, tea! TEA."), [("tea", 3)])

    def test_keeps_apostrophes(self):
        self.assertEqual(count_words("don't stop"), [("don't", 1), ("stop", 1)])

    def test_empty_text_has_no_words(self):
        self.assertEqual(count_words(""), [])
