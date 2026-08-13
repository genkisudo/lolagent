import tempfile
import unittest
from pathlib import Path
from lol_agent.ingest import ingest_json
from lol_agent.questions import parse_question
from lol_agent.resolve import answer


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.temp.name) / "agent.duckdb")
        ingest_json("examples/t1_gen_g_game2.json", self.db, str(Path(self.temp.name) / "raw"))

    def tearDown(self): self.temp.cleanup()

    def test_elemental_dragons_exclude_elder(self):
        result = answer(self.db, "T1 vs Gen.G", parse_question("Both Teams Slay a Dragon?", 2))
        self.assertEqual(result.result, "YES")
        self.assertNotIn("ELDER", " ".join(result.evidence))

    def test_missing_multikill_is_unknown(self):
        result = answer(self.db, "T1 vs Gen.G", parse_question("Any Player Quadra Kill?", 2))
        self.assertEqual(result.result, "UNKNOWN")

    def test_complete_timeline_can_support_a_negative_team_objective_result(self):
        result = answer(self.db, "Gen.G vs T1", parse_question("Did Gen.G slay Baron Nashor?", 2))
        self.assertEqual(result.result, "NO")

    def test_inhibitor_count_uses_explicit_timeline_events(self):
        result = answer(self.db, "T1 vs Gen.G", parse_question("How many inhibitors did Team A destroy?", 2))
        self.assertEqual(result.result, "1")

    def test_game_is_not_silently_selected_for_multigame_series(self):
        result = answer(self.db, "T1 vs Gen.G", parse_question("Who won?"))
        self.assertEqual(result.result, "TEAM_A")


if __name__ == "__main__": unittest.main()
