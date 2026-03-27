from django.urls import path
from .views import FoodSearchView, AiFoodSearchView, AiPhotoFoodScanView, BarcodeLookupView

urlpatterns = [
    path('search/', FoodSearchView.as_view(), name='food-search'),
    path('ai-search/', AiFoodSearchView.as_view(), name='ai-food-search'),
    path('ai-scan/', AiPhotoFoodScanView.as_view(), name='ai-food-photo-scan'),
    path('barcode/<str:barcode>/', BarcodeLookupView.as_view(), name='barcode-lookup'),
]
