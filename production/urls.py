from django.urls import path

from production.views import BoxMakerView, BoxOrderView, PrinterView, PrintingJobView, PrintingView, TracingStudioView, TracingView

urlpatterns = [
    path("printers/", PrinterView.as_view(), name="printer"),
    path("printers/<uuid:printer_id>/", PrinterView.as_view(), name="printer-detail"),
    path("tracing-studios/", TracingStudioView.as_view(), name="tracing-studio"),
    path("tracing-studios/<uuid:tracing_studio_id>/", TracingStudioView.as_view(), name="tracing-studio-detail"),
    path("box-makers/", BoxMakerView.as_view(), name="box-maker"),
    path("box-makers/<uuid:box_maker_id>/", BoxMakerView.as_view(), name="box-maker-detail"),
    path("box-orders/", BoxOrderView.as_view(), name="box-order"),
    path("box-orders/<uuid:box_order_id>/", BoxOrderView.as_view(), name="box-order-detail"),
    path("printing-jobs/<uuid:printing_job_id>/", PrintingJobView.as_view(), name="printing-job-detail"),
    path("printing/", PrintingView.as_view(), name="printing-list"),
    path("tracing/", TracingView.as_view(), name="tracing-list"),
]
