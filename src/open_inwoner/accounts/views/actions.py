from datetime import datetime

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http.response import HttpResponseRedirect
from django.urls.base import reverse_lazy
from django.views.generic import CreateView, ListView
from django.views.generic.edit import UpdateView

from ..forms import ActionForm, ActionListForm
from ..models import Action


class BaseActionFilter:
    def get_actions(self, actions):
        print(self.request.GET.get("end_date"))
        if self.request.GET.get("end_date"):
            end_date = datetime.strptime(
                self.request.GET.get("end_date"), "%d-%m-%Y"
            ).date()
            print(end_date)
            actions = actions.filter(end_date=end_date)
        if self.request.GET.get("created_by"):
            actions = actions.filter(created_by=self.request.GET.get("created_by"))
        if self.request.GET.get("status"):
            actions = actions.filter(status=self.request.GET.get("status"))
        return actions


class ActionListView(LoginRequiredMixin, BaseActionFilter, ListView):
    template_name = "pages/profile/actions/list.html"
    model = Action
    paginate_by = 10

    def get_queryset(self):
        base_qs = super().get_queryset()
        return base_qs.filter(created_by=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["action_form"] = ActionListForm(data=self.request.GET)
        context["actions"] = self.get_actions(self.get_queryset())
        return context


class ActionUpdateView(LoginRequiredMixin, UpdateView):
    template_name = "pages/profile/actions/edit.html"
    model = Action
    slug_field = "uuid"
    slug_url_kwarg = "uuid"
    form_class = ActionForm
    success_url = reverse_lazy("accounts:action_list")

    def get_queryset(self):
        base_qs = super().get_queryset()
        return base_qs.filter(created_by=self.request.user)

    def form_valid(self, form):
        self.object = form.save(self.request.user)
        return HttpResponseRedirect(self.get_success_url())


class ActionCreateView(LoginRequiredMixin, CreateView):
    template_name = "pages/profile/actions/edit.html"
    model = Action
    form_class = ActionForm
    success_url = reverse_lazy("accounts:action_list")

    def form_valid(self, form):
        self.object = form.save(self.request.user)
        return HttpResponseRedirect(self.get_success_url())
