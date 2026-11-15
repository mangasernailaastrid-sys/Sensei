import unittest
from types import SimpleNamespace
from bot import target_error


def member(identity, role):
    return SimpleNamespace(id=identity, top_role=role)


class HierarchyTests(unittest.TestCase):
    def test_lower_role_allowed(self):
        self.assertIsNone(target_error(member(1, 5), member(2, 2), member(3, 8), 9))

    def test_equal_or_higher_caller_role_rejected(self):
        for role in (5, 6):
            self.assertIsNotNone(target_error(member(1, 5), member(2, role), member(3, 8), 9))

    def test_protected_identities(self):
        for identity in (1, 3, 9):
            self.assertIsNotNone(target_error(member(1, 5), member(identity, 1), member(3, 8), 9))

    def test_owner_still_needs_bot_hierarchy(self):
        self.assertIsNone(target_error(member(9, 1), member(2, 5), member(3, 8), 9))
        self.assertIsNotNone(target_error(member(9, 1), member(2, 8), member(3, 8), 9))


if __name__ == '__main__':
    unittest.main()
