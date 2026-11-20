"""Расчёт совместимости навыков: проверки без обращения к БД.

Критерии приёмки из `docs/contracts.md` (Sprint 8, совместимость в карточке
заявки): 0%, 75%, 100%, округление «1 из 8» до 13%, пустые требования,
независимость от дополнительных навыков и от требований соседней роли.
"""

import uuid
from types import SimpleNamespace

from django.test import SimpleTestCase

from applications.services import skill_match


def skill(name, category="hard"):
    """Минимальная запись справочника: расчёту нужны только pk и name."""
    return SimpleNamespace(pk=uuid.uuid4(), name=name, category=category)


class SkillMatchCalculationTests(SimpleTestCase):
    def test_no_required_skills_means_no_percent(self):
        python = skill("Python")
        result = skill_match([python], [])
        self.assertIsNone(result["match_percent"])
        self.assertEqual(result["required_count"], 0)
        self.assertEqual(result["matched_count"], 0)
        self.assertEqual(result["matched_skills"], [])
        self.assertEqual(result["missing_skills"], [])
        # «Профиль минус роль»: без требований все навыки кандидата дополнительные.
        self.assertEqual([item["name"] for item in result["extra_skills"]], ["Python"])
        self.assertTrue(result["candidate_has_skills"])

    def test_empty_profile_with_requirements_gives_zero_percent(self):
        result = skill_match([], [skill("Python"), skill("Django")])
        self.assertEqual(result["match_percent"], 0)
        self.assertEqual(result["matched_count"], 0)
        self.assertEqual(result["required_count"], 2)
        self.assertFalse(result["candidate_has_skills"])
        self.assertEqual([item["name"] for item in result["missing_skills"]], ["Django", "Python"])

    def test_seventy_five_and_one_hundred_percent(self):
        python, django, docker, sql = (
            skill("Python"), skill("Django"), skill("Docker"), skill("SQL"),
        )
        required = [python, django, docker, sql]
        seventy_five = skill_match([python, django, docker, skill("Figma")], required)
        self.assertEqual(seventy_five["match_percent"], 75)
        self.assertEqual(seventy_five["matched_count"], 3)
        self.assertEqual(seventy_five["required_count"], 4)
        hundred = skill_match(required, required)
        self.assertEqual(hundred["match_percent"], 100)
        self.assertEqual(hundred["missing_skills"], [])
        self.assertEqual(hundred["extra_skills"], [])

    def test_one_of_eight_rounds_up_to_thirteen(self):
        required = [skill(f"Skill {number}") for number in range(8)]
        result = skill_match([required[0]], required)
        self.assertEqual(result["match_percent"], 13)
        self.assertEqual(result["matched_count"], 1)
        self.assertEqual(result["required_count"], 8)

    def test_half_percent_rounds_up(self):
        # 100 × 1 / 8 = 12.5 → 13, а 100 × 1 / 3 = 33.33 → 33.
        required_three = [skill("A"), skill("B"), skill("C")]
        self.assertEqual(skill_match([required_three[0]], required_three)["match_percent"], 33)
        required_eight = [skill(f"S{number}") for number in range(8)]
        self.assertEqual(skill_match([required_eight[0]], required_eight)["match_percent"], 13)

    def test_extra_skills_do_not_change_percent(self):
        required = [skill("Python"), skill("Django")]
        extra = [skill("Figma"), skill("SQL"), skill("Docker")]
        with_extras = skill_match([*required, *extra], required)
        without_extras = skill_match(required, required)
        self.assertEqual(with_extras["match_percent"], without_extras["match_percent"])
        self.assertEqual(
            [item["name"] for item in with_extras["extra_skills"]], ["Docker", "Figma", "SQL"],
        )

    def test_hard_and_soft_skills_have_equal_weight(self):
        hard, soft = skill("Python", "hard"), skill("Коммуникация", "soft")
        result = skill_match([soft], [hard, soft])
        self.assertEqual(result["match_percent"], 50)
        self.assertEqual([item["name"] for item in result["matched_skills"]], ["Коммуникация"])

    def test_groups_are_sorted_and_do_not_overlap(self):
        python, django, figma = skill("Python"), skill("Django"), skill("Figma")
        result = skill_match([python, figma], [django, python])
        self.assertEqual([item["name"] for item in result["matched_skills"]], ["Python"])
        self.assertEqual([item["name"] for item in result["missing_skills"]], ["Django"])
        self.assertEqual([item["name"] for item in result["extra_skills"]], ["Figma"])
        names = [
            item["name"]
            for group in ("matched_skills", "missing_skills", "extra_skills")
            for item in result[group]
        ]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(sorted(names), ["Django", "Figma", "Python"])

    def test_same_skill_id_is_counted_once(self):
        python = skill("Python")
        result = skill_match([python, python], [python, python])
        self.assertEqual(result["match_percent"], 100)
        self.assertEqual(result["matched_count"], 1)
        self.assertEqual(result["required_count"], 1)
