#!/usr/bin/env python3
import unittest

from reviewers_pr_guard import parse_names


class ParseNames(unittest.TestCase):
    def test_skips_comments_and_blank(self):
        text = "# GitHub usernames\n\nvinybrun\n# later\n  Alice  \n@bob extra\n"
        self.assertEqual(parse_names(text), {"vinybrun", "alice", "bob"})

    def test_detects_remove_and_add(self):
        base = parse_names("vinybrun\nalice\n")
        head_remove = parse_names("vinybrun\n")
        head_add = parse_names("vinybrun\nalice\ncarol\n")
        self.assertEqual(base - head_remove, {"alice"})
        self.assertEqual(head_add - base, {"carol"})


if __name__ == "__main__":
    unittest.main()
