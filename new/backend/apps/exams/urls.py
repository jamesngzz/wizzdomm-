from rest_framework.routers import DefaultRouter
from .views import ExamViewSet, QuestionViewSet


router = DefaultRouter()
router.register(r"exams", ExamViewSet, basename="exam")
router.register(r"questions", QuestionViewSet, basename="question")

urlpatterns = router.urls


