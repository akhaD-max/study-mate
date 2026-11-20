"""Совместимость навыков на странице «Входящие заявки» (Sprint 8).

Проверяется поведение `applications:incoming` по контракту: блок считается
по навыкам кандидата и требованиям его роли, не зависит от дополнительных
навыков и соседней роли, обновляется после изменения требований, не меняет
доступность действий руководителя и не растит число запросов с числом заявок.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import Skill
from applications.models import Application
from applications.services import list_project_applications, submit_application
from projects.models import Category, Project, ProjectRole


class IncomingSkillMatchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model().objects
        cls.author = users.create_user("owner@example.com", "Password!1")
        cls.candidate = users.create_user("candidate@example.com", "Password!1")
        cls.category = Category.objects.create(name="Разработка", slug="development")
        # Справочник уже засеян миграцией accounts.0003: берём существующие
        # записи, а при необходимости создаём их, не нарушая уникальность.
        def skill(name, category=Skill.Category.HARD):
            return Skill.objects.get_or_create(name=name, defaults={"category": category})[0]

        cls.python = skill("Python")
        cls.django = skill("Django")
        cls.docker = skill("Docker")
        cls.figma = skill("Figma")
        cls.soft = skill("Коммуникация", Skill.Category.SOFT)
        cls.project = Project.objects.create(
            author=cls.author, category=cls.category, title="Платформа",
        )
        cls.role = ProjectRole.objects.create(project=cls.project, name="Backend", capacity=2)
        cls.role.required_skills.set([cls.python, cls.django, cls.docker, cls.figma])
        cls.neighbour_role = ProjectRole.objects.create(
            project=cls.project, name="Frontend", capacity=1,
        )
        cls.neighbour_role.required_skills.set([cls.soft])

    def setUp(self):
        self.candidate.skills.set([self.python, self.django, self.docker])
        self.application = submit_application(
            user=self.candidate, project_id=self.project.pk,
            role_id=self.role.pk, comment="Хочу в команду",
        )

    def page(self):
        self.client.force_login(self.author)
        return self.client.get(reverse("applications:incoming", args=[self.project.pk]))

    def test_page_shows_percent_and_three_groups(self):
        response = self.page()
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Совместимость по навыкам")
        self.assertContains(response, "75% · совпало 3 из 4 навыков")
        self.assertContains(response, "Совпадают")
        self.assertContains(response, "Не хватает")
        self.assertNotContains(response, "Дополнительные навыки")
        self.assertContains(response, "Figma")
        # Для заявки на рассмотрении подписи «по текущим навыкам» ещё нет.
        self.assertNotContains(response, "По текущим навыкам и требованиям роли")

    def test_matched_and_missing_are_visible_extra_skills_collapsed(self):
        # Совпавшие и недостающие навыки видны сразу, дополнительные — только
        # после раскрытия. Единственный <details> — группа дополнительных.
        self.candidate.skills.add(self.soft)
        response = self.page()
        html = response.content.decode()
        # Кроме меню пользователя в шапке других раскрывашек нет.
        self.assertEqual(html.count("<details"), 2)
        self.assertNotIn('<details class="in-skill-group" open', html)
        self.assertIn('class="in-skill-group in-skill-extra"', html)
        matched_block = html.split("Совпадают", 1)[1].split("</div>", 1)[0]
        self.assertIn("Python", matched_block)
        missing_block = html.split("Не хватает", 1)[1].split("</div>", 1)[0]
        self.assertIn("Figma", missing_block)

    def test_template_comment_is_not_rendered(self):
        # Многострочный {# #} Django не поддерживает — текст утекал в HTML.
        response = self.page()
        self.assertNotContains(response, "Навыки скрыты по умолчанию")
        self.assertNotContains(response, "работает без JS")
        self.assertNotContains(response, "{#")

    def test_extra_skills_are_shown_without_changing_percent(self):
        self.candidate.skills.add(self.soft)
        response = self.page()
        self.assertContains(response, "75% · совпало 3 из 4 навыков")
        self.assertContains(response, "Дополнительные навыки")
        self.assertContains(response, "Коммуникация")

    def test_neighbour_role_requirements_do_not_affect_result(self):
        # Требование соседней роли (Коммуникация) не входит в расчёт по Backend.
        self.candidate.skills.set([self.python, self.django, self.docker, self.soft])
        response = self.page()
        self.assertContains(response, "75% · совпало 3 из 4 навыков")
        applications = list_project_applications(
            user=self.author, project_id=self.project.pk,
        )[1]
        match = applications[0].skill_match
        self.assertEqual(
            [item["name"] for item in match["missing_skills"]], ["Figma"],
        )

    def test_full_match_reaches_one_hundred(self):
        self.candidate.skills.set([self.python, self.django, self.docker, self.figma])
        self.assertContains(self.page(), "100% · совпало 4 из 4 навыков")

    def test_empty_role_requirements_show_no_data(self):
        self.role.required_skills.clear()
        response = self.page()
        self.assertContains(response, "Нет данных")
        self.assertContains(response, "У роли не заданы требуемые навыки.")
        self.assertNotContains(response, "% · совпало")

    def test_candidate_without_skills_shows_zero_percent(self):
        self.candidate.skills.clear()
        response = self.page()
        self.assertContains(response, "0% · совпало 0 из 4 навыков")
        self.assertContains(response, "Кандидат пока не указал навыки.")

    def test_result_refreshes_after_requirements_change(self):
        self.assertContains(self.page(), "75% · совпало 3 из 4 навыков")
        self.role.required_skills.set([self.python, self.django, self.docker])
        self.assertContains(self.page(), "100% · совпало 3 из 3 навыков")

    def test_one_of_eight_rounds_to_thirteen_percent(self):
        extra = [
            Skill.objects.create(name=f"Навык {number}", category=Skill.Category.HARD)
            for number in range(7)
        ]
        self.role.required_skills.set([self.python, *extra])
        self.candidate.skills.set([self.python])
        self.assertContains(self.page(), "13% · совпало 1 из 8 навыков")

    def test_reviewed_application_shows_current_state_note(self):
        self.application.status = Application.Status.ACCEPTED
        self.application.save(update_fields=["status"])
        response = self.page()
        self.assertContains(response, "По текущим навыкам и требованиям роли")
        # Совместимость не возвращает действия руководителя отклонённой заявке.
        self.assertNotContains(response, "Принять")

    def test_match_does_not_change_actions_or_status(self):
        response = self.page()
        self.assertContains(response, "Принять")
        self.assertContains(response, "Отклонить")
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, Application.Status.PENDING)

    def test_only_author_sees_incoming_page(self):
        self.client.force_login(self.candidate)
        self.assertEqual(
            self.client.get(reverse("applications:incoming", args=[self.project.pk])).status_code,
            403,
        )

    def test_page_is_rendered_after_review_error(self):
        # Заявку уже рассмотрели: повторное принятие даёт ошибку и возвращает
        # страницу, которая тоже должна получить блок совместимости.
        self.application.status = Application.Status.REJECTED
        self.application.save(update_fields=["status"])
        self.client.force_login(self.author)
        response = self.client.post(
            reverse("applications:accept", args=[self.application.pk]),
        )
        self.assertEqual(response.status_code, 200)
        # Повторный рендер после ошибки тоже получает блок совместимости.
        self.assertContains(response, "Совместимость по навыкам")
        self.assertContains(response, "75% · совпало 3 из 4 навыков")

    def test_query_count_does_not_grow_with_applications(self):
        users = get_user_model().objects
        for number in range(4):
            extra_candidate = users.create_user(f"extra{number}@example.com", "Password!1")
            extra_candidate.skills.set([self.python])
            submit_application(
                user=extra_candidate, project_id=self.project.pk, role_id=self.role.pk,
            )
        self.client.force_login(self.author)
        url = reverse("applications:incoming", args=[self.project.pk])
        self.client.get(url)  # прогрев сессии и справочников
        with self.assertNumQueries(7):
            # сессия, пользователь, проверка сессии в middleware, проект,
            # заявки, навыки кандидатов, требования ролей
            self.client.get(url)
