from types import SimpleNamespace
from uuid import UUID

from django.test import SimpleTestCase

from applications.services import skill_match


def skill(number, name):
    return SimpleNamespace(pk=UUID(int=number), name=name)


class SkillMatchTests(SimpleTestCase):
    def test_rounding_sets_order_and_extra_skills(self):
        required = [skill(i, f"Skill {i}") for i in range(1, 9)]
        extra = skill(20, "Extra")
        result = skill_match([required[0], required[0], extra], required)
        self.assertEqual(result["match_percent"], 13)
        self.assertEqual((result["matched_count"], result["required_count"]), (1, 8))
        self.assertEqual(result["matched_skills"], [{"id": required[0].pk, "name": "Skill 1"}])
        self.assertEqual([item["name"] for item in result["missing_skills"]],
                         [f"Skill {i}" for i in range(2, 9)])
        self.assertEqual(result["extra_skills"], [{"id": extra.pk, "name": "Extra"}])
        self.assertTrue(result["candidate_has_skills"])

    def test_no_requirements_no_candidate_and_full_match(self):
        skills = [skill(i, f"Skill {i}") for i in range(1, 5)]
        self.assertIsNone(skill_match(skills, [])["match_percent"])
        empty = skill_match([], skills)
        self.assertEqual(empty["match_percent"], 0)
        self.assertFalse(empty["candidate_has_skills"])
        self.assertEqual(len(empty["missing_skills"]), 4)
        self.assertEqual(skill_match(skills[:3], skills)["match_percent"], 75)
        self.assertEqual(skill_match(skills, skills)["match_percent"], 100)
