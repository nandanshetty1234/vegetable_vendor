from django.urls import path
from . import views

urlpatterns = [
    path('', views.vegetable_list, name='vegetable_list'),
    path('report/', views.report_page, name='report_page'),
    path('set_date/', views.set_date, name='set_date'),
    path('add/', views.add_vegetable, name='add_vegetable'),
    path('delete/', views.delete_vegetable, name='delete_vegetable'),
    path('calculate/', views.calculate_totals, name='calculate_totals'),
    path('save/', views.save_data, name='save_data'),  # Save Button URL
    path('ajax/price-chart/', views.price_chart, name='price_chart'),
    path('ajax/grouped-bar-chart/', views.grouped_bar_chart, name='grouped_bar_chart'),
    path('ajax/stacked-profit-loss-chart/', views.stacked_profit_loss_chart, name='stacked_profit_loss_chart'),
    path('monthly-analysis/', views.monthly_analysis, name='monthly_analysis'),
    path('ajax/monthly-analysis-data/', views.monthly_analysis_data, name='monthly_analysis_data'),




    
]
