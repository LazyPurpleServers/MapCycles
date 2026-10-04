import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "reenumerate_missioncycles.py"
SPEC = importlib.util.spec_from_file_location("reenumerate_missioncycles", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class ReenumerateTests(unittest.TestCase):
    def test_corrects_count_and_gap_while_preserving_formatting(self) -> None:
        source = (
            '"cycle"\r\n'
            '{\r\n'
            '\t"categories" "1"\r\n'
            '\t"1"\r\n'
            '\t{\r\n'
            '\t\t"count" "99"\r\n'
            '\t\t"4" { "map" "first" } // keep this\r\n'
            '\t\t// "5" { "map" "disabled" }\r\n'
            '\t\t"12" { "map" "second" }\r\n'
            '\t}\r\n'
            '}\r\n'
        )

        corrected, categories, missions = MODULE.reenumerate(source)

        self.assertEqual(categories, 1)
        self.assertEqual(missions, 2)
        self.assertIn('\t\t"count" "2"\r\n', corrected)
        self.assertIn('\t\t"1" { "map" "first" } // keep this\r\n', corrected)
        self.assertIn('\t\t"2" { "map" "second" }\r\n', corrected)
        self.assertIn('// "5" { "map" "disabled" }', corrected)
        self.assertEqual(corrected.count("\r\n"), source.count("\r\n"))

    def test_processes_each_category_independently(self) -> None:
        source = '''"cycle"
{
    "categories" "2"
    "1" { "count" "1" "8" { "map" "a" } }
    "2" { "count" "7" "3" { "map" "b" } "9" { "map" "c" } }
}
'''

        corrected, categories, missions = MODULE.reenumerate(source)

        self.assertEqual((categories, missions), (2, 3))
        self.assertIn('"1" { "count" "1" "1" { "map" "a" } }', corrected)
        self.assertIn(
            '"2" { "count" "2" "1" { "map" "b" } "2" { "map" "c" } }',
            corrected,
        )

    def test_is_idempotent(self) -> None:
        source = '"cycle" { "categories" "1" "1" { "count" "1" "1" {} } }'
        corrected, _, _ = MODULE.reenumerate(source)
        corrected_again, _, _ = MODULE.reenumerate(corrected)
        self.assertEqual(corrected_again, source)

    def test_rejects_incorrect_category_structure(self) -> None:
        source = '"cycle" { "categories" "2" "1" { "count" "0" } }'
        with self.assertRaisesRegex(MODULE.MissioncycleError, "does not match"):
            MODULE.reenumerate(source)

    def test_rejects_missing_count(self) -> None:
        source = '"cycle" { "categories" "1" "1" { "1" {} } }'
        with self.assertRaisesRegex(MODULE.MissioncycleError, "exactly one scalar"):
            MODULE.reenumerate(source)


if __name__ == "__main__":
    unittest.main()
