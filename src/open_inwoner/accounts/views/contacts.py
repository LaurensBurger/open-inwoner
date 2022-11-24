from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http.response import HttpResponseRedirect
from django.urls.base import reverse, reverse_lazy
from django.utils.functional import cached_property
from django.utils.translation import gettext as _
from django.views.generic import ListView
from django.views.generic.edit import DeleteView, FormView, UpdateView

from view_breadcrumbs import BaseBreadcrumbMixin

from open_inwoner.utils.views import LogMixin

from ..choices import ContactTypeChoices
from ..forms import ContactFilterForm, ContactCreateForm, ContactUpdateForm

from ..models import Contact, Invite, User


class ContactListView(LoginRequiredMixin, BaseBreadcrumbMixin, ListView):
    template_name = "pages/profile/contacts/list.html"
    model = User
    paginate_by = 10

    @cached_property
    def crumbs(self):
        return [
            (_("Mijn profiel"), reverse("accounts:my_profile")),
            (_("Mijn contacten"), reverse("accounts:contact_list")),
        ]

    def get_queryset(self):
        base_qs = super().get_queryset()

        current_user = self.request.user
        user_contacts = current_user.user_contacts.all()
        contacts_for_approval = current_user.contacts_for_approval.all()
        base_qs = user_contacts | contacts_for_approval

        type_filter = self.request.GET.get("type")

        if type_filter:
            base_qs = base_qs.filter(contact_type=type_filter)

        return base_qs.order_by("-date_joined")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context[
            "pending_invitations"
        ] = Invite.objects.get_pending_invitations_for_user(self.request.user)
        context["form"] = ContactFilterForm(data=self.request.GET)
        return context


class ContactUpdateView(LogMixin, LoginRequiredMixin, BaseBreadcrumbMixin, UpdateView):
    template_name = "pages/profile/contacts/edit.html"
    model = User
    slug_field = "uuid"
    slug_url_kwarg = "uuid"
    form_class = ContactUpdateForm
    success_url = reverse_lazy("accounts:contact_list")

    @cached_property
    def crumbs(self):
        return [
            (_("Mijn profiel"), reverse("accounts:my_profile")),
            (_("Mijn contacten"), reverse("accounts:contact_list")),
            (
                _("Bewerk {}").format(self.object.get_full_name()),
                reverse("accounts:contact_edit", kwargs=self.kwargs),
            ),
        ]

    def get_queryset(self):
        base_qs = super().get_queryset()

        current_user = self.request.user
        base_qs = current_user.user_contacts.all()
        return base_qs

    def form_valid(self, form):
        self.object = form.save()

        self.log_change(self.object, _("contact was modified"))
        return HttpResponseRedirect(self.get_success_url())


class ContactCreateView(LogMixin, LoginRequiredMixin, BaseBreadcrumbMixin, FormView):
    template_name = "pages/profile/contacts/edit.html"
    form_class = ContactCreateForm
    success_url = reverse_lazy("accounts:contact_list")

    @cached_property
    def crumbs(self):
        return [
            (_("Mijn profiel"), reverse("accounts:my_profile")),
            (_("Mijn contacten"), reverse("accounts:contact_list")),
            (
                _("Maak contact aan"),
                reverse("accounts:contact_create", kwargs=self.kwargs),
            ),
        ]

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "user": self.request.user}

    def form_valid(self, form):
        cleaned_data = form.cleaned_data
        email = cleaned_data["email"]
        user = self.request.user
        contact_user = User.objects.filter(email=email)

        # Adding a contact-user which already exists in the platform
        if contact_user.exists():
            user.contacts_for_approval.add(contact_user[0])

        # New contact-user which triggers an invite
        else:
            invite = Invite.objects.create(
                inviter=self.request.user,
                invitee_email=email,
                invitee_first_name=cleaned_data["first_name"],
                invitee_last_name=cleaned_data["last_name"],
            )
            invite.send(self.request)

        # FIXME type off message
        messages.add_message(
            self.request,
            messages.SUCCESS,
            _(
                "{contact} is toegevoegd aan uw contactpersonen.".format(
                    contact=contact_user[0]
                    if contact_user.exists()
                    else f"{cleaned_data['first_name']} {cleaned_data['last_name']}"
                )
            ),
        )
        if contact_user.exists():
            self.log_addition(
                contact_user[0],
                _("contact was created"),
            )
        return HttpResponseRedirect(self.get_success_url())


class ContactDeleteView(LogMixin, LoginRequiredMixin, DeleteView):
    model = User
    slug_field = "uuid"
    slug_url_kwarg = "uuid"
    success_url = reverse_lazy("accounts:contact_list")

    def get_queryset(self):
        base_qs = super().get_queryset()

        current_user = self.request.user
        base_qs = current_user.user_contacts.all()
        return base_qs

    def delete(self, request, *args, **kwargs):
        object = self.get_object()

        current_user = self.request.user

        # Remove relationship between the two users
        current_user.user_contacts.remove(object)

        self.log_deletion(object, _("contact was deleted"))
        return HttpResponseRedirect(self.success_url)
