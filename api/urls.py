from django.urls import path

from rest_framework.routers import DefaultRouter

# API views
from .views import EmailRegistration
from .views import EmailAuthorization
from .views import EmailApprove
from .views import PasswordRecovery
from .views import ProfileAPIView
from .views import ProfileCarsAPIView

# View sets
from .views import MastersViewSet
from .views import UserReportViewSet
from .views import RequestForCooperationViewSet
from .views import CarBrandReadOnlyViewSet
from .views import CarReadOnlyViewSet
from .views import RepairCategoryReadOnlyViewSet
from .views import OfferImageReadOnlyViewSet
from .views import GradeReadOnlyViewSet
from .views import GradePhotoReadOnlyViewSet
from .views import CommentViewSet
from .views import CommentMediaReadOnlyViewSet
from .views import RepairOfferViewSet
from .views import PublicRepairOfferViewSet
from .views import SubscriptionViewSet
from .views import ChatReadOnlyViewSet
from .views import MessageViewSet
from .views import FAQReadOnlyViewSet
from .views import FAQTopicReadOnlyViewSet
from .views import FAQContentReadOnlyViewSet

router = DefaultRouter()

router.register('masters', MastersViewSet)
router.register('reports', UserReportViewSet)
router.register('cooperation', RequestForCooperationViewSet)
router.register('car_brands', CarBrandReadOnlyViewSet)
router.register('cars', CarReadOnlyViewSet)
router.register('categories', RepairCategoryReadOnlyViewSet)
router.register('offer_images', OfferImageReadOnlyViewSet)
router.register('grades', GradeReadOnlyViewSet)
router.register('grade_photos', GradePhotoReadOnlyViewSet)
router.register('comments', CommentViewSet)
router.register('comments_media', CommentMediaReadOnlyViewSet)
router.register('offers', RepairOfferViewSet)
router.register('public_offers', PublicRepairOfferViewSet)
router.register('subscription', SubscriptionViewSet)
router.register('chats', ChatReadOnlyViewSet)
router.register('messages', MessageViewSet)
router.register('faq', FAQReadOnlyViewSet)
router.register('faq_topics', FAQTopicReadOnlyViewSet)
router.register('faq_content', FAQContentReadOnlyViewSet)

urlpatterns = [
    path('registration/', EmailRegistration.as_view()),
    path('authorization/', EmailAuthorization.as_view()),
    path('email_approve/', EmailApprove.as_view()),
    path('password_recovery/', PasswordRecovery.as_view()),
    path('profile/cars/', ProfileCarsAPIView.as_view()),
    path('profile/', ProfileAPIView.as_view()),

]
urlpatterns += router.urls
