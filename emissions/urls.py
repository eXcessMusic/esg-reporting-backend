from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'projections', views.ProjectionViewSet, basename='projection')

urlpatterns = [
    path('', views.APIRoot.as_view(), name='api-root'),
    path('reports/', views.ReportList.as_view(), name='report-list'),
    path('reports/<int:pk>/', views.ReportDetail.as_view(), name='report-detail'),
    path('reports/<int:pk>/sources/', views.ReportSourcesView.as_view(), name='report-sources'),
    path('reports/<int:pk>/projected-emissions/', views.ReportProjectedEmissionsView.as_view(), name='report-projected-emissions'),
    path('reports/<int:pk>/add-strategy/', views.ReportAddStrategyView.as_view(), name='report-add-strategy'),
    path('reports/<int:pk>/remove-strategy/', views.ReportRemoveStrategyView.as_view(), name='report-remove-strategy'),

    path('sources/', views.SourceList.as_view(), name='source-list'),
    path('sources/<int:pk>/', views.SourceDetail.as_view(), name='source-detail'),
    path('sources/<int:pk>/emissions-by-year/', views.source_emissions_by_year, name='source-emissions-by-year'),
    path('sources/<int:pk>/total-emission/', views.source_total_emission, name='source-total-emission'),
    path('sources/<int:pk>/modifications/', views.source_modifications, name='source-modifications'),

    path('reduction-strategies/', views.ReductionStrategyList.as_view(), name='reductionstrategy-list'),
    path('reduction-strategies/<int:pk>/', views.ReductionStrategyDetail.as_view(), name='reductionstrategy-detail'),
    path('reduction-strategies/<int:pk>/total-reduction/', views.ReductionStrategyTotalReductionView.as_view(), name='reductionstrategy-total-reduction'),
    path('reduction-strategies/<int:pk>/modifications/', views.ReductionStrategyModificationsView.as_view(), name='reductionstrategy-modifications'),

    path('modifications/', views.ModificationList.as_view(), name='modification-list'),
    path('modifications/<int:pk>/', views.ModificationDetail.as_view(), name='modification-detail'),

    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
]

# Adding the router to the project for the projections viewset
urlpatterns += router.urls