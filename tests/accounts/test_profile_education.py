from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.forms import ProfileForm
from accounts.models import EducationLevel, EducationStatus, Skill

User = get_user_model()

PASSWORD = "StudyMate-safe-password!"


def payload(**overrides):
    data = {
        "full_name": "Иван Петров",
        "university": "МГУ",
        "specialty": "Прикладная информатика",
        "education_status": EducationStatus.STUDYING,
        "education_level": EducationLevel.BACHELOR,
        "course": "3",
        "desired_role": "",
        "bio": "Люблю Django.",
        "skills": [],
    }
    data.update(overrides)
    return data


class ProfileEducationFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="student@example.com", password=PASSWORD)
        self.skill, _ = Skill.objects.get_or_create(
            name="Python", defaults={"category": Skill.Category.HARD}
        )

    def test_course_choices_depend_on_selected_level(self):
        expected = {
            EducationLevel.BACHELOR: [1, 2, 3, 4],
            EducationLevel.SPECIALIST: [1, 2, 3, 4, 5],
            EducationLevel.MASTER: [1, 2],
            EducationLevel.POSTGRADUATE: [1, 2, 3],
        }
        for level, courses in expected.items():
            with self.subTest(level=level):
                form = ProfileForm(data=payload(education_level=level))
                self.assertEqual(
                    [number for number, _ in form.fields["course"].choices],
                    ["", *courses],
                )
                self.assertFalse(form.fields["course"].disabled)

    def test_course_is_disabled_without_level(self):
        form = ProfileForm(data=payload(education_level=""))
        self.assertEqual(list(form.fields["course"].choices), [("", "Выберите курс")])
        self.assertTrue(form.fields["course"].disabled)

    def test_studying_requires_level(self):
        form = ProfileForm(
            data=payload(
                education_status=EducationStatus.STUDYING,
                education_level="",
                course="",
                skills=[self.skill.pk],
            )
        )
        self.assertFalse(form.is_valid())
        self.assertIn("education_level", form.errors)

    def test_chosen_level_requires_course(self):
        form = ProfileForm(
            data=payload(
                education_status=EducationStatus.STUDYING,
                education_level=EducationLevel.BACHELOR,
                course="",
                skills=[self.skill.pk],
            )
        )
        self.assertFalse(form.is_valid())
        self.assertIn("course", form.errors)

    def test_course_outside_level_range_is_rejected(self):
        form = ProfileForm(
            data=payload(education_level=EducationLevel.MASTER, course="4")
        )
        self.assertFalse(form.is_valid())
        self.assertIn("course", form.errors)

    def test_graduated_clears_course(self):
        form = ProfileForm(
            data=payload(
                education_status=EducationStatus.GRADUATED,
                education_level=EducationLevel.MASTER,
                course="2",
                skills=[self.skill.pk],
            )
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIsNone(form.cleaned_data["course"])

    def test_graduated_profile_ignores_course_in_database(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("profiles:edit"),
            payload(
                education_status=EducationStatus.GRADUATED,
                education_level=EducationLevel.BACHELOR,
                course="2",
                skills=[str(self.skill.pk)],
            ),
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.education_status, EducationStatus.GRADUATED)
        self.assertEqual(self.user.education_level, EducationLevel.BACHELOR)
        self.assertIsNone(self.user.course)

    def test_saving_studying_profile_persists_course(self):
        self.client.force_login(self.user)
        self.client.post(
            reverse("profiles:edit"),
            payload(
                education_level=EducationLevel.SPECIALIST,
                course="5",
                skills=[str(self.skill.pk)],
            ),
        )
        self.user.refresh_from_db()
        self.assertEqual(self.user.education_status, EducationStatus.STUDYING)
        self.assertEqual(self.user.education_level, EducationLevel.SPECIALIST)
        self.assertEqual(self.user.course, 5)


class ProfileEducationPageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="owner@example.com",
            password=PASSWORD,
            full_name="Мария Иванова",
            university="ВШЭ",
            education_status=EducationStatus.STUDYING,
            education_level=EducationLevel.MASTER,
            course=1,
        )
        self.client.force_login(self.user)

    def test_edit_page_renders_education_controls(self):
        response = self.client.get(reverse("profiles:edit"))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn('id="id_education_status"', html)
        self.assertIn('id="id_education_level"', html)
        self.assertIn('id="id_course"', html)
        self.assertIn("Обучаюсь", html)
        self.assertIn("Закончил обучение", html)
        self.assertIn("Бакалавриат", html)
        self.assertIn("Аспирантура", html)

    def test_detail_page_shows_education_summary(self):
        response = self.client.get(
            reverse("profiles:detail", kwargs={"user_id": self.user.pk})
        )
        self.assertContains(response, "Обучаюсь · магистратура · 1 курс")

    def test_detail_page_hides_course_for_graduates(self):
        self.user.education_status = EducationStatus.GRADUATED
        self.user.course = None
        self.user.save()
        response = self.client.get(
            reverse("profiles:detail", kwargs={"user_id": self.user.pk})
        )
        self.assertContains(response, "Закончил обучение · магистратура")
        self.assertNotContains(response, "1 курс")
