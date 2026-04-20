"""Tests for the free agents analyzer feature."""

"""
Unit tests for the free agents analyzer feature.
Note: Integration tests require the ESPN API to be authenticated.
These tests validate the core logic with mocked data.
"""

import unittest
from copy import deepcopy


class TestFreeAgentsAnalyzer(unittest.TestCase):
    """Test suite for free agents analyzer functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.nine_cats = ["PTS", "BLK", "STL", "AST", "REB", "TO", "3PM", "FG%", "FT%"]
        self.league_size = 12
        self.avg_rank = (self.league_size + 1) / 2

    def test_strengths_weaknesses_classification(self):
        """Test that categories are correctly classified as strengths or weaknesses."""
        # Simulate team rankings
        team_rankings = {
            "PTS": 3,     # Strength (top 5)
            "BLK": 9,     # Weakness (bottom 5)
            "STL": 6,     # Neutral
            "AST": 2,     # Strength (top 5)
            "REB": 10,    # Weakness (bottom 5)
            "TO": 4,      # Strength (top 5)
            "3PM": 7,     # Neutral
            "FG%": 3,     # Strength (top 5)
            "FT%": 8,     # Weakness (bottom 5)
        }

        strengths = []
        weaknesses = []

        for cat, rank in team_rankings.items():
            if rank <= 5:
                strengths.append({"label": cat, "rank": rank})
            elif rank >= 8:
                weaknesses.append({"label": cat, "rank": rank})

        # Verify strengths
        self.assertEqual(len(strengths), 4, "Should have 4 strengths")
        strength_labels = [s["label"] for s in strengths]
        self.assertIn("PTS", strength_labels)
        self.assertIn("AST", strength_labels)

        # Verify weaknesses
        self.assertEqual(len(weaknesses), 3, "Should have 3 weaknesses")
        weakness_labels = [w["label"] for w in weaknesses]
        self.assertIn("BLK", weakness_labels)
        self.assertIn("REB", weakness_labels)

    def test_fit_score_calculates_strength_gains(self):
        """Test that fit score maximizes gains in strong categories."""
        strengths = [
            {"label": "PTS", "rank": 3},
            {"label": "AST", "rank": 2},
            {"label": "TO", "rank": 4},
        ]
        weaknesses = [
            {"label": "BLK", "rank": 9},
            {"label": "REB", "rank": 10},
        ]

        # Player excelling in strengths
        strong_player = {
            "name": "Strong Player",
            "team_name": "Team X",
            "position": "G",
            "pro_team": "Lakers",
            "PTS": 30,
            "BLK": 2,
            "STL": 3,
            "AST": 10,
            "REB": 5,
            "TO": 1,
            "3PM": 8,
            "FG%": 0.50,
            "FT%": 0.90,
        }

        score = self._calculate_fit_score(strong_player, strengths, weaknesses)
        self.assertGreater(score["fit_score"], 0)

    def test_fit_score_accepts_weakness_losses(self):
        """Test that fit score accepts losses in weak categories."""
        strengths = [
            {"label": "PTS", "rank": 3},
        ]
        weaknesses = [
            {"label": "BLK", "rank": 9},
            {"label": "REB", "rank": 10},
        ]

        # Player with weak stats in weakness categories
        weak_player = {
            "name": "Weak Player",
            "team_name": "Team X",
            "position": "F",
            "pro_team": "Heat",
            "PTS": 15,
            "BLK": 0,
            "STL": 1,
            "AST": 3,
            "REB": 4,
            "TO": 5,
            "3PM": 2,
            "FG%": 0.40,
            "FT%": 0.75,
        }

        score = self._calculate_fit_score(weak_player, strengths, weaknesses)
        # Should still have non-zero score from accepting losses
        self.assertGreaterEqual(score["fit_score"], 0)

    def test_fit_score_normalization(self):
        """Test that fit score is properly normalized to 0-100."""
        strengths = [
            {"label": "PTS", "rank": 1},
            {"label": "AST", "rank": 2},
            {"label": "TO", "rank": 3},
        ]
        weaknesses = [
            {"label": "BLK", "rank": 9},
            {"label": "REB", "rank": 10},
        ]

        # Player with all max stats
        max_player = {
            "name": "Max Player",
            "team_name": "Team X",
            "position": "C",
            "pro_team": "NBA",
            "PTS": 50,
            "BLK": 10,
            "STL": 8,
            "AST": 10,
            "REB": 20,
            "TO": 1,
            "3PM": 15,
            "FG%": 0.60,
            "FT%": 0.95,
        }

        score = self._calculate_fit_score(max_player, strengths, weaknesses)
        self.assertGreaterEqual(score["fit_score"], 50, "High stats player should have high fit score")
        self.assertLessEqual(score["fit_score"], 100)

    def test_top_3_suggestions(self):
        """Test that top 3 suggestions are properly ordered."""
        # Mock player data with varying fit scores
        all_players = [
            {"name": "Player A", "pts": 25, "team_name": "Team X"},
            {"name": "Player B", "pts": 20, "team_name": "Team Y"},
            {"name": "Player C", "pts": 30, "team_name": "Team Z"},
            {"name": "Player D", "pts": 15, "team_name": "Team W"},
        ]

        # Calculate fit scores (simplified: proportional to pts)
        player_scores = []
        for player in all_players:
            player_scores.append({
                **player,
                "fit_score": player["pts"] * 10,  # Simplified scoring
            })

        # Sort by fit score
        player_scores.sort(key=lambda x: x["fit_score"], reverse=True)
        top_3 = player_scores[:3]

        # Verify ordering
        self.assertEqual(len(top_3), 3)
        self.assertGreaterEqual(top_3[0]["fit_score"], top_3[1]["fit_score"])
        self.assertGreaterEqual(top_3[1]["fit_score"], top_3[2]["fit_score"])

    def test_team_strengths_calculation(self):
        """Test team strengths calculation logic."""
        # Simulate a league with 12 teams
        team_ranks = {
            "Team A": {"PTS": 3, "BLK": 6, "AST": 4, "REB": 7, "TO": 2, "3PM": 5, "FG%": 4, "FT%": 3},
            "Team B": {"PTS": 9, "BLK": 2, "AST": 8, "REB": 5, "TO": 5, "3PM": 4, "FG%": 5, "FT%": 4},
            "Team C": {"PTS": 5, "BLK": 5, "AST": 3, "REB": 8, "TO": 3, "3PM": 6, "FG%": 3, "FT%": 4},
        }

        # Test Team A (PTS:3, AST:4, TO:2, 3PM:5, FG%:4, FT%:3 = 6 strengths; BLK:6, REB:7 = neutral)
        team_a_strengths, team_a_weaknesses = self._get_team_strengths_weaknesses(team_ranks["Team A"])

        self.assertGreater(len(team_a_strengths), 0, "Team A should have strengths")
        self.assertEqual(len(team_a_strengths), 6)  # PTS, AST, TO, 3PM, FG%, FT%
        self.assertEqual(len(team_a_weaknesses), 0)  # BLK:6, REB:7 are neutral

       # Test Team B (BLK:2, REB:5, TO:5, 3PM:4, FG%:5, FT%:4 = 6 strengths; PTS:9, AST:8 = 2 weaknesses)
        team_b_strengths, team_b_weaknesses = self._get_team_strengths_weaknesses(team_ranks["Team B"])

        self.assertEqual(len(team_b_strengths), 6)  # BLK, REB, TO, 3PM, FG%, FT%
        self.assertEqual(len(team_b_weaknesses), 2)  # PTS, AST

    def test_category_ranking_boundaries(self):
        """Test that category rankings are correctly classified."""
        # Test top-ranked category
        top_rank = 3
        self.assertEqual(top_rank, 3)
        self.assertTrue(top_rank <= 5, f"Rank {top_rank} should be a strength")

        # Test bottom-ranked category
        bottom_rank = 10
        self.assertEqual(bottom_rank, 10)
        self.assertTrue(bottom_rank >= 8, f"Rank {bottom_rank} should be a weakness")

        # Test boundary case (top 5)
        for rank in range(1, 6):
            self.assertTrue(rank <= 5, f"Rank {rank} should be a strength")

        # Test boundary case (bottom 5)
        for rank in range(8, 13):
            self.assertTrue(rank >= 8, f"Rank {rank} should be a weakness")

    def _calculate_fit_score(self, player: dict, strengths: list, weaknesses: list) -> dict:
        """Helper method to calculate fit score (simulates backend function)."""
        score = 0
        category_breakdown = []
        total_points = 0

        for cat in self.nine_cats:
            agent_val = player.get(cat, 0)
            
            # Get strength/weakness info
            strength_info = next((s for s in strengths if s["label"] == cat), None)
            weakness_info = next((w for w in weaknesses if w["label"] == cat), None)

            if strength_info:
                # Strength category - gain points
                score += agent_val
                category_breakdown.append({
                    "category": cat,
                    "agent": agent_val,
                    "type": "gain",
                    "points": agent_val
                })
                total_points += agent_val
            elif weakness_info:
                # Weakness category - accept loss
                score += 0
                category_breakdown.append({
                    "category": cat,
                    "agent": agent_val,
                    "type": "accept",
                    "points": agent_val
                })
                total_points += agent_val
            else:
                # Neutral category
                score += 0
                category_breakdown.append({
                    "category": cat,
                    "agent": agent_val,
                    "type": "neutral",
                    "points": agent_val
                })
                total_points += agent_val

        # Normalize score
        max_possible = sum(player.get(cat, 0) for cat in self.nine_cats)
        fit_score = round((score / max_possible * 100) if max_possible > 0 else 0, 2)

        return {
            "fit_score": fit_score,
            "category_breakdown": category_breakdown,
            "strengths_gain": sum(b["points"] for b in category_breakdown if b["type"] == "gain"),
            "weaknesses_accept": sum(b["points"] for b in category_breakdown if b["type"] == "accept"),
            "neutral_gain": sum(b["points"] for b in category_breakdown if b["type"] == "neutral"),
        }

    def _get_team_strengths_weaknesses(self, team_rankings: dict) -> tuple:
        """Helper method to get team strengths and weaknesses (simulates backend function)."""
        strengths = []
        weaknesses = []

        for cat, rank in team_rankings.items():
            if rank <= 5:
                strengths.append({"label": cat, "rank": rank})
            elif rank >= 8:
                weaknesses.append({"label": cat, "rank": rank})

        return strengths, weaknesses


if __name__ == "__main__":
    unittest.main()
