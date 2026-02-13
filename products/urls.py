from django.urls import path
from products import views

urlpatterns = [
    path("categories/", views.CategoriesListView.as_view(), name="categories-list"),
    path("products/", views.ProductsListView.as_view(), name="products-list"),
    path("products/<slug:slug>/", views.ProductBySlugView.as_view(), name="product-by-slug"),
    path("admin/products/", views.AdminProductsView.as_view(), name="admin-products"),
    path("admin/products/<uuid:id>/", views.AdminProductDetailView.as_view(), name="admin-product-detail"),
    path("admin/products/<uuid:id>/reviews/", views.AdminProductReviewsView.as_view(), name="admin-product-reviews"),
    path(
        "admin/products/<uuid:id>/reviews/<uuid:review_id>/",
        views.AdminProductReviewDetailView.as_view(),
        name="admin-product-review-detail",
    ),
]