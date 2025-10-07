# expenditures/urls.py
from django.urls import path

from .views import (
    # Dashboard & JSON helpers
    ExpenditureDashboardView,
    RawStockJSON,
    ProcessedStockJSON,

    # 1. Budget lines & direct expenditures (cash-out)
    BudgetLineListView, BudgetLineCreateView, BudgetLineUpdateView, BudgetLineDeleteView,
    ExpenditureListView, ExpenditureCreateView, ExpenditureUpdateView, ExpenditureDeleteView,
    ExpenditureDetailView, ExpenditureReportView,

    # 2. Inventory (raw / processed / batches / consumption)
    SeasonalProductListView,  SeasonalProductCreateView,
    SeasonalProductUpdateView, SeasonalProductDeleteView,

    ProcessedProductListView, ProcessedProductCreateView,
    ProcessedProductUpdateView, ProcessedProductDeleteView,

    SeasonalPurchaseListView, SeasonalPurchaseCreateView,
    SeasonalPurchaseUpdateView, SeasonalPurchaseDeleteView,

    ProcessingBatchListView,  ProcessingBatchCreateView,
    ProcessingBatchUpdateView, ProcessingBatchDeleteView,

    DailyConsumptionListView, DailyConsumptionCreateView,
    DailyConsumptionUpdateView, DailyConsumptionDeleteView,

    StockDashboardView,

    # 3. Kitchen module
    KitchenDashboardView,
    KitchenProductListView,  KitchenProductCreateView,  KitchenProductUpdateView,  KitchenProductDeleteView,
    KitchenPurchaseListView, KitchenPurchaseCreateView, KitchenPurchaseUpdateView, KitchenPurchaseDeleteView,
    KitchenUsageListView,    KitchenUsageCreateView,    KitchenUsageUpdateView,    KitchenUsageDeleteView,
)

###############################################################################
# URL patterns
###############################################################################

urlpatterns: list[path] = [
    # ─── Dashboard ────────────────────────────────────────────────────────
    path("dashboard/", ExpenditureDashboardView.as_view(), name="expenditure_dashboard"),

    # AJAX helpers
    path("ajax/raw-stock/",       RawStockJSON.as_view(),       name="ajax_raw_stock"),
    path("ajax/processed-stock/", ProcessedStockJSON.as_view(), name="ajax_processed_stock"),

    # ─── Budget lines ────────────────────────────────────────────────────
    path("budgetlines/",                   BudgetLineListView.as_view(),   name="budgetline_list"),
    path("budgetlines/create/",            BudgetLineCreateView.as_view(), name="budgetline_create"),
    path("budgetlines/<int:pk>/update/",   BudgetLineUpdateView.as_view(), name="budgetline_update"),
    path("budgetlines/<int:pk>/delete/",   BudgetLineDeleteView.as_view(), name="budgetline_delete"),

    # ─── Direct expenditures (cash-out) ──────────────────────────────────
    path("expenditures/",                   ExpenditureListView.as_view(),   name="expenditure_list"),
    path("expenditures/create/",            ExpenditureCreateView.as_view(), name="expenditure_create"),
    path("expenditures/<int:pk>/update/",   ExpenditureUpdateView.as_view(), name="expenditure_update"),
    path("expenditures/<int:pk>/delete/",   ExpenditureDeleteView.as_view(), name="expenditure_delete"),
    path("expenditures/<int:pk>/",          ExpenditureDetailView.as_view(), name="expenditure_detail"),

    # Periodic expenditure reports (daily / weekly / monthly)
    path(
        "expenditures/reports/<str:period>/",
        ExpenditureReportView.as_view(),
        name="expenditure_report",
    ),

    # ─── Seasonal raw products ───────────────────────────────────────────
    path("inventory/products/",                   SeasonalProductListView.as_view(),   name="seasonalproduct_list"),
    path("inventory/products/create/",            SeasonalProductCreateView.as_view(), name="seasonalproduct_create"),
    path("inventory/products/<int:pk>/update/",   SeasonalProductUpdateView.as_view(), name="seasonalproduct_update"),
    path("inventory/products/<int:pk>/delete/",   SeasonalProductDeleteView.as_view(), name="seasonalproduct_delete"),

    # ─── Processed products ──────────────────────────────────────────────
    path("inventory/processed/",                   ProcessedProductListView.as_view(),   name="processedproduct_list"),
    path("inventory/processed/create/",            ProcessedProductCreateView.as_view(), name="processedproduct_create"),
    path("inventory/processed/<int:pk>/update/",   ProcessedProductUpdateView.as_view(), name="processedproduct_update"),
    path("inventory/processed/<int:pk>/delete/",   ProcessedProductDeleteView.as_view(), name="processedproduct_delete"),

    # ─── Seasonal purchases (raw commodity buys) ─────────────────────────
    path("inventory/purchases/",                   SeasonalPurchaseListView.as_view(),   name="seasonalpurchase_list"),
    path("inventory/purchases/create/",            SeasonalPurchaseCreateView.as_view(), name="seasonalpurchase_create"),
    path("inventory/purchases/<int:pk>/update/",   SeasonalPurchaseUpdateView.as_view(), name="seasonalpurchase_update"),
    path("inventory/purchases/<int:pk>/delete/",   SeasonalPurchaseDeleteView.as_view(), name="seasonalpurchase_delete"),

    # ─── Processing batches ──────────────────────────────────────────────
    path("inventory/processing/",                   ProcessingBatchListView.as_view(),   name="processingbatch_list"),
    path("inventory/processing/create/",            ProcessingBatchCreateView.as_view(), name="processingbatch_create"),
    path("inventory/processing/<int:pk>/update/",   ProcessingBatchUpdateView.as_view(), name="processingbatch_update"),
    path("inventory/processing/<int:pk>/delete/",   ProcessingBatchDeleteView.as_view(), name="processingbatch_delete"),

    # ─── Daily consumption (kitchen use of processed stock) ──────────────
    path("inventory/consumption/",                   DailyConsumptionListView.as_view(),   name="dailyconsumption_list"),
    path("inventory/consumption/create/",            DailyConsumptionCreateView.as_view(), name="dailyconsumption_create"),
    path("inventory/consumption/<int:pk>/update/",   DailyConsumptionUpdateView.as_view(), name="dailyconsumption_update"),
    path("inventory/consumption/<int:pk>/delete/",   DailyConsumptionDeleteView.as_view(), name="dailyconsumption_delete"),

    # ─── Stock dashboards ────────────────────────────────────────────────
    path("inventory/stock/",     StockDashboardView.as_view(),   name="stock_dashboard"),
    path("kitchen/dashboard/",   KitchenDashboardView.as_view(), name="kitchen_dashboard"),

    # ─── Kitchen products ────────────────────────────────────────────────
    path("kitchen/products/",                 KitchenProductListView.as_view(),   name="kitchenproduct_list"),
    path("kitchen/products/add/",             KitchenProductCreateView.as_view(), name="kitchenproduct_create"),
    path("kitchen/products/<int:pk>/edit/",   KitchenProductUpdateView.as_view(), name="kitchenproduct_update"),
    path("kitchen/products/<int:pk>/delete/", KitchenProductDeleteView.as_view(), name="kitchenproduct_delete"),

    # ─── Kitchen purchases ───────────────────────────────────────────────
    path("kitchen/purchases/",                 KitchenPurchaseListView.as_view(),   name="kitchenpurchase_list"),
    path("kitchen/purchases/add/",             KitchenPurchaseCreateView.as_view(), name="kitchenpurchase_create"),
    path("kitchen/purchases/<int:pk>/edit/",   KitchenPurchaseUpdateView.as_view(), name="kitchenpurchase_update"),
    path("kitchen/purchases/<int:pk>/delete/", KitchenPurchaseDeleteView.as_view(), name="kitchenpurchase_delete"),

    # ─── Kitchen usages ──────────────────────────────────────────────────
    path("kitchen/usages/",                 KitchenUsageListView.as_view(),   name="kitchenusage_list"),
    path("kitchen/usages/add/",             KitchenUsageCreateView.as_view(), name="kitchenusage_create"),
    path("kitchen/usages/<int:pk>/edit/",   KitchenUsageUpdateView.as_view(), name="kitchenusage_update"),
    path("kitchen/usages/<int:pk>/delete/", KitchenUsageDeleteView.as_view(), name="kitchenusage_delete"),
]
