from django.urls import path
from django.views.generic import RedirectView

from open_inwoner.accounts.views.cases import (
    CaseDetailView,
    CaseDocumentDownloadView,
    ClosedCaseListView,
    OpenCaseListView,
    OpenSubmissionListView,
)
from open_inwoner.accounts.views.contactmoments import (
    KlantContactMomentDetailView,
    KlantContactMomentListView,
)

app_name = "cases"

urlpatterns = [
    path("closed/", ClosedCaseListView.as_view(), name="closed_cases"),
    path("forms/", OpenSubmissionListView.as_view(), name="open_submissions"),
    path(
        "contactmomenten/",
        KlantContactMomentListView.as_view(),
        name="contactmoment_list",
    ),
    path(
        "contactmomenten/<str:kcm_uuid>/",
        KlantContactMomentDetailView.as_view(),
        name="contactmoment_detail",
    ),
    path(
        "<str:object_id>/document/<str:info_id>/",
        CaseDocumentDownloadView.as_view(),
        name="document_download",
    ),
    path(
        "<str:object_id>/status/",
        CaseDetailView.as_view(),
        name="case_detail",
    ),
    path("open/", RedirectView.as_view(pattern_name="cases:open_cases"), name="index"),
    path("", OpenCaseListView.as_view(), name="open_cases"),
]
