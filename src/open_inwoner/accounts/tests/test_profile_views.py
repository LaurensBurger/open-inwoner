from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from django_webtest import WebTest

from open_inwoner.accounts.choices import StatusChoices
from open_inwoner.pdc.tests.factories import CategoryFactory

from ...questionnaire.tests.factories import QuestionnaireStepFactory
from ..choices import LoginTypeChoices
from .factories import ActionFactory, DocumentFactory, UserFactory


class ProfileViewTests(WebTest):
    def setUp(self):
        self.url = reverse("accounts:my_profile")
        self.return_url = reverse("logout")
        self.user = UserFactory()

        self.action_deleted = ActionFactory(
            name="deleted action, should not show up",
            created_by=self.user,
            is_deleted=True,
            status=StatusChoices.open,
        )

    def test_login_required(self):
        login_url = reverse("login")
        response = self.app.get(self.url)
        self.assertRedirects(response, f"{login_url}?next={self.url}")

    def test_get_empty_profile_page(self):
        response = self.app.get(self.url, user=self.user)

        self.assertEquals(response.status_code, 200)
        self.assertContains(response, _("U heeft geen intressegebieden aangegeven."))
        self.assertContains(response, _("U heeft nog geen contacten."))
        self.assertContains(response, "0 acties staan open.")
        self.assertNotContains(response, reverse("questionnaire:questionnaire_list"))

    def test_get_filled_profile_page(self):
        ActionFactory(created_by=self.user)
        contact = UserFactory()
        self.user.user_contacts.add(contact)
        category = CategoryFactory()
        self.user.selected_themes.add(category)
        QuestionnaireStepFactory(published=True)

        response = self.app.get(self.url, user=self.user)
        self.assertEquals(response.status_code, 200)
        self.assertContains(response, category.name)
        self.assertContains(
            response,
            f"{contact.first_name} ({contact.get_contact_type_display()})",
        )
        self.assertContains(response, "1 acties staan open.")
        self.assertContains(response, reverse("questionnaire:questionnaire_list"))

    def test_only_open_actions(self):
        action = ActionFactory(created_by=self.user, status=StatusChoices.closed)
        response = self.app.get(self.url, user=self.user)
        self.assertEquals(response.status_code, 200)
        self.assertContains(response, "0 acties staan open.")

    def test_deactivate_account(self):
        response = self.app.get(self.url, user=self.user)
        self.assertEquals(response.status_code, 200)
        form = response.forms["deactivate-form"]
        base_response = form.submit()
        self.assertEquals(base_response.url, self.return_url)
        followed_response = base_response.follow().follow()
        self.assertEquals(followed_response.status_code, 200)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertIsNotNone(self.user.deactivated_on)

    def test_deactivate_account_staff(self):
        self.user.is_staff = True
        self.user.save()
        response = self.app.get(self.url, user=self.user)
        self.assertEquals(response.status_code, 200)
        form = response.forms["deactivate-form"]
        base_response = form.submit()
        self.assertEquals(base_response.url, self.url)
        followed_response = base_response.follow()
        self.assertEquals(followed_response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertIsNone(self.user.deactivated_on)

    def test_deactivate_account_digid(self):
        """
        check that user is redirected to digid:logout
        """
        user = UserFactory.create(
            login_type=LoginTypeChoices.digid, email="john@smith.nl"
        )

        response = self.app.get(self.url, user=user)
        self.assertEquals(response.status_code, 200)
        form = response.forms["deactivate-form"]

        response = form.submit()

        self.assertEquals(response.status_code, 302)
        self.assertEquals(response.url, reverse("digid:logout"))

    def test_get_documents_sorted(self):
        """
        check that the new document is shown first
        """
        doc_old = DocumentFactory.create(name="some-old", owner=self.user)
        doc_new = DocumentFactory.create(name="some-new", owner=self.user)

        response = self.app.get(self.url, user=self.user)
        self.assertEquals(response.status_code, 200)

        file_tags = response.html.find(class_="file-list").find_all(
            class_="file-list__list-item"
        )
        self.assertEquals(len(file_tags), 2)
        self.assertTrue(doc_new.name in file_tags[0].prettify())
        self.assertTrue(doc_old.name in file_tags[1].prettify())


class EditProfileTests(WebTest):
    def setUp(self):
        self.url = reverse("accounts:edit_profile")
        self.return_url = reverse("accounts:my_profile")
        self.user = UserFactory()

    def test_login_required(self):
        login_url = reverse("login")
        response = self.app.get(self.url)
        self.assertRedirects(response, f"{login_url}?next={self.url}")

    def test_save_form(self):
        response = self.app.get(self.url, user=self.user)
        self.assertEquals(response.status_code, 200)
        form = response.forms["profile-edit"]
        base_response = form.submit()
        self.assertEquals(base_response.url, self.return_url)
        followed_response = base_response.follow()
        self.assertEquals(followed_response.status_code, 200)

    def test_save_empty_form_fails(self):
        response = self.app.get(self.url, user=self.user, status=200)
        form = response.forms["profile-edit"]
        form["first_name"] = ""
        form["last_name"] = ""
        form["email"] = ""
        form["phonenumber"] = ""
        form["birthday"] = ""
        form["street"] = ""
        form["housenumber"] = ""
        form["postcode"] = ""
        form["city"] = ""
        base_response = form.submit()
        expected_errors = {"email": [_("Dit veld is vereist.")]}
        self.assertEqual(base_response.context["form"].errors, expected_errors)

    def test_save_filled_form(self):
        response = self.app.get(self.url, user=self.user, status=200)
        form = response.forms["profile-edit"]
        form["first_name"] = "First name"
        form["last_name"] = "Last name"
        form["email"] = "user@example.com"
        form["phonenumber"] = "06987878787"
        form["birthday"] = "21-01-1992"
        form["street"] = "Keizersgracht"
        form["housenumber"] = "17 d"
        form["postcode"] = "1013 RM"
        form["city"] = "Amsterdam"
        base_response = form.submit()
        self.assertEquals(base_response.url, self.return_url)
        followed_response = base_response.follow()
        self.assertEquals(followed_response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEquals(self.user.first_name, "First name")
        self.assertEquals(self.user.last_name, "Last name")
        self.assertEquals(self.user.email, "user@example.com")
        self.assertEquals(self.user.birthday.strftime("%d-%m-%Y"), "21-01-1992")
        self.assertEquals(self.user.street, "Keizersgracht")
        self.assertEquals(self.user.housenumber, "17 d")
        self.assertEquals(self.user.postcode, "1013 RM")
        self.assertEquals(self.user.city, "Amsterdam")

    def test_save_with_invalid_first_name_chars_fails(self):
        invalid_characters = "/\"\\,.:;'"

        for char in invalid_characters:
            with self.subTest(char=char):
                response = self.app.get(self.url, user=self.user, status=200)
                form = response.forms["profile-edit"]
                form["first_name"] = char
                form["last_name"] = "Last name"
                form["phonenumber"] = "06987878787"
                form["birthday"] = "21-01-1992"
                form["street"] = "Keizersgracht"
                form["housenumber"] = "17 d"
                form["postcode"] = "1013 RM"
                form["city"] = "Amsterdam"
                response = form.submit()
                expected_errors = {
                    "first_name": [
                        _("Uw invoer bevat een ongeldig teken: {char}").format(
                            char=char
                        )
                    ]
                }
                self.assertEqual(response.context["form"].errors, expected_errors)

    def test_save_with_invalid_last_name_chars_fails(self):
        invalid_characters = "/\"\\,.:;'"

        for char in invalid_characters:
            with self.subTest(char=char):
                response = self.app.get(self.url, user=self.user, status=200)
                form = response.forms["profile-edit"]
                form["first_name"] = "John"
                form["last_name"] = char
                form["phonenumber"] = "06987878787"
                form["birthday"] = "21-01-1992"
                form["street"] = "Keizersgracht"
                form["housenumber"] = "17 d"
                form["postcode"] = "1013 RM"
                form["city"] = "Amsterdam"
                response = form.submit()
                expected_errors = {
                    "last_name": [
                        _("Uw invoer bevat een ongeldig teken: {char}").format(
                            char=char
                        )
                    ]
                }
                self.assertEqual(response.context["form"].errors, expected_errors)

    def test_modify_email_succeeds(self):
        response = self.app.get(self.url, user=self.user)
        form = response.forms["profile-edit"]
        form["email"] = "user@example.com"
        response = form.submit()
        self.assertEqual(self.user.email, self.user.email)
        self.user.refresh_from_db()
        self.assertEqual(response.url, self.return_url)
        self.assertEqual(self.user.email, "user@example.com")


class EditIntrestsTests(WebTest):
    def setUp(self):
        self.url = reverse("accounts:my_themes")
        self.user = UserFactory()

    def test_login_required(self):
        login_url = reverse("login")
        response = self.app.get(self.url)
        self.assertRedirects(response, f"{login_url}?next={self.url}")

    def test_preselected_values(self):
        category = CategoryFactory(name="a")
        CategoryFactory(name="b")
        CategoryFactory(name="c")
        self.user.selected_themes.add(category)
        response = self.app.get(self.url, user=self.user)
        form = response.forms["change-themes"]
        self.assertTrue(form.get("selected_themes", index=0).checked)
        self.assertFalse(form.get("selected_themes", index=1).checked)
        self.assertFalse(form.get("selected_themes", index=2).checked)


class ExportProfileTests(WebTest):
    def setUp(self):
        self.url = reverse("accounts:profile_export")
        self.user = UserFactory()

    def test_login_required(self):
        login_url = reverse("login")
        response = self.app.get(self.url)
        self.assertRedirects(response, f"{login_url}?next={self.url}")

    def test_export_profile(self):
        response = self.app.get(self.url, user=self.user)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, "application/pdf")
        self.assertEqual(
            response["Content-Disposition"],
            f'attachment; filename="profile.pdf"',
        )
