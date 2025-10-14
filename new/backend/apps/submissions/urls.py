from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import SubmissionViewSet, GradeItemAPIView, ItemDetailAPIView, ItemImageDeleteView
from .views import ItemAppendImageView


router = DefaultRouter()
router.register(r"submissions", SubmissionViewSet, basename="submission")

urlpatterns = router.urls
urlpatterns += [
    path("items/<int:item_id>/grade/", GradeItemAPIView.as_view(), name="grade-item"),
    path("items/<int:item_id>/images/<int:image_index>/", ItemImageDeleteView.as_view(), name="item-image-delete"),
    path("items/<int:item_id>/", ItemDetailAPIView.as_view(), name="item-detail"),
    path("items/<int:item_id>/append-image/", ItemAppendImageView.as_view(), name="item-append-image"),
]


