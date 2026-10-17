import io
import os
import tempfile
import unittest

from wordfreq.cli import main


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    code = main(argv, stdout=out, stderr=err)
    return code, out.getvalue(), err.getvalue()


class CliTest(unittest.TestCase):
    def setUp(self):
        handle, self.path = tempfile.mkstemp(suffix=".txt")
        with os.fdopen(handle, "w") as file:
            file.write("the cat and the hat and the bat")

    def tearDown(self):
        os.remove(self.path)

    def test_prints_each_word_with_its_count(self):
        code, out, err = run([self.path])
        self.assertEqual(code, 0)
        self.assertEqual(out, "the 3\nand 2\nbat 1\ncat 1\nhat 1\n")
        self.assertEqual(err, "")

    def test_missing_file_exits_2(self):
        code, out, err = run(["/no/such/file.txt"])
        self.assertEqual((code, out), (2, ""))
        self.assertEqual(err, "error: cannot read /no/such/file.txt\n")

    def test_no_arguments_prints_usage(self):
        code, out, err = run([])
        self.assertEqual((code, out), (2, ""))
        self.assertEqual(err, "usage: wordfreq FILE\n")
