from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from products.models import Category, Product, ProductReview
from products.permissions import IsAdmin
from products.paginations import ProductsPagination
from products.serializers import (
    CategorySerializer,
    ProductSerializer,
    AdminProductWriteSerializer,
    ProductReviewSerializer,
    AdminReviewPatchSerializer,
)




class CategoriesListView(generics.ListAPIView):
    """
    List product categories.

    Method:
      - GET

    Response:
      - 200 OK: list of categories
    """

    permission_classes = (permissions.AllowAny,)
    serializer_class = CategorySerializer
    queryset = Category.objects.all().order_by("title")


class ProductsListView(generics.ListAPIView):
    """
    List products with filters, search, sorting, and pagination.

    Method:
      - GET

    Query params:
      - category: string (category slug)
      - inStock: 1|0
      - minPrice: int (toman)
      - maxPrice: int (toman)
      - sort: string (newest|price_asc|price_desc|rating_desc)
      - q: string (search in title/description/sku/brand)
      - page: int
      - pageSize: int

    Response:
      - 200 OK: paginated items
        {
          "items": Product[],
          "page": number,
          "pageSize": number,
          "total": number
        }
    """

    permission_classes = (permissions.AllowAny,)
    serializer_class = ProductSerializer
    pagination_class = ProductsPagination

    def get_queryset(self):
        qs = (
            Product.objects.select_related("category")
            .prefetch_related("images", "specs")
            .all()
        )

        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category__slug=category)

        in_stock = self.request.query_params.get("inStock")
        if in_stock in ("0", "1"):
            qs = qs.filter(in_stock=(in_stock == "1"))

        min_price = self.request.query_params.get("minPrice")
        if min_price and str(min_price).isdigit():
            qs = qs.filter(price_toman__gte=int(min_price))

        max_price = self.request.query_params.get("maxPrice")
        if max_price and str(max_price).isdigit():
            qs = qs.filter(price_toman__lte=int(max_price))

        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(
                Q(title__icontains=q)
                | Q(short_description__icontains=q)
                | Q(description__icontains=q)
                | Q(sku__icontains=q)
                | Q(brand__icontains=q)
            )

        sort = self.request.query_params.get("sort")
        if sort == "price_asc":
            qs = qs.order_by("price_toman", "-created_at")
        elif sort == "price_desc":
            qs = qs.order_by("-price_toman", "-created_at")
        elif sort == "rating_desc":
            qs = qs.order_by("-rating", "-created_at")
        else:
            qs = qs.order_by("-created_at")

        return qs


class ProductBySlugView(generics.RetrieveAPIView):
    """
    Retrieve product details by slug.

    Method:
      - GET

    URL params:
      - slug: string

    Response:
      - 200 OK: product details
      - 404 Not Found: product not found
    """

    permission_classes = (permissions.AllowAny,)
    serializer_class = ProductSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return (
            Product.objects.select_related("category")
            .prefetch_related("images", "specs", "reviews__author")
            .all()
        )


class AdminProductsView(generics.ListCreateAPIView):
    """
    Admin list and create products.

    Methods:
      - GET: list products
      - POST: create product

    Auth:
      - Requires: Authorization: Bearer <access_token>
      - Requires: is_admin == True

    GET query params:
      - q: string (search by title/slug/sku/brand)
      - category: string (category slug)
      - inStock: true|false|1|0

    POST input (JSON):
      - title: string
      - slug: string
      - shortDescription: string
      - description: string (optional)
      - sku: string (optional)
      - brand: string (optional)
      - categorySlug: string
      - priceToman: int
      - compareAtPriceToman: int (optional)
      - inStock: bool
      - stockQuantity: int (optional)
      - rating: number (optional)

    Responses:
      - 200 OK: list products
      - 201 Created: product created
      - 400 Bad Request: validation error
      - 401 Unauthorized: missing/invalid token
      - 403 Forbidden: not admin
    """

    permission_classes = (IsAdmin,)

    def get_serializer_class(self):
        if self.request.method == "POST":
            return AdminProductWriteSerializer
        return ProductSerializer

    def get_queryset(self):
        qs = (
            Product.objects.select_related("category")
            .prefetch_related("images", "specs")
            .all()
            .order_by("-created_at")
        )

        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(
                Q(title__icontains=q)
                | Q(slug__icontains=q)
                | Q(sku__icontains=q)
                | Q(brand__icontains=q)
            )

        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category__slug=category)

        in_stock = self.request.query_params.get("inStock")
        if in_stock is not None:
            if str(in_stock).lower() in ("true", "1"):
                qs = qs.filter(in_stock=True)
            elif str(in_stock).lower() in ("false", "0"):
                qs = qs.filter(in_stock=False)

        return qs


class AdminProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Admin retrieve, update, and delete a product.

    Methods:
      - GET: retrieve product
      - PATCH/PUT: update product
      - DELETE: delete product

    Auth:
      - Requires: Authorization: Bearer <access_token>
      - Requires: is_admin == True

    URL params:
      - id: string (UUID)

    PATCH/PUT input (JSON):
      - same fields as create (partial allowed for PATCH)

    Responses:
      - 200 OK: product returned/updated
      - 204 No Content: product deleted
      - 400 Bad Request: validation error
      - 401 Unauthorized: missing/invalid token
      - 403 Forbidden: not admin
      - 404 Not Found: product not found
    """

    permission_classes = (IsAdmin,)
    queryset = Product.objects.select_related("category").prefetch_related("images", "specs").all()
    lookup_field = "id"

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return AdminProductWriteSerializer
        return ProductSerializer


class AdminProductReviewsView(generics.ListAPIView):
    """
    Admin list reviews for a product.

    Method:
      - GET

    Auth:
      - Requires: Authorization: Bearer <access_token>
      - Requires: is_admin == True

    URL params:
      - id: string (product UUID)

    Response:
      - 200 OK: list of reviews
      - 401 Unauthorized: missing/invalid token
      - 403 Forbidden: not admin
      - 404 Not Found: product not found
    """

    permission_classes = (IsAdmin,)
    serializer_class = ProductReviewSerializer

    def get_queryset(self):
        product = get_object_or_404(Product, id=self.kwargs["id"])
        return ProductReview.objects.filter(product=product).select_related("author").order_by("-created_at")


class AdminProductReviewDetailView(APIView):
    """
    Admin update or delete a review for a product.

    Methods:
      - PATCH: update review status
      - DELETE: delete review

    Auth:
      - Requires: Authorization: Bearer <access_token>
      - Requires: is_admin == True

    URL params:
      - id: string (product UUID)
      - review_id: string (review UUID)

    PATCH input (JSON):
      - status: pending|approved|rejected

    Responses:
      - 200 OK: updated review
      - 204 No Content: review deleted
      - 400 Bad Request: validation error
      - 401 Unauthorized: missing/invalid token
      - 403 Forbidden: not admin
      - 404 Not Found: product or review not found
    """

    permission_classes = (IsAdmin,)

    def patch(self, request, id, review_id):
        product = get_object_or_404(Product, id=id)
        review = get_object_or_404(ProductReview, id=review_id, product=product)

        s = AdminReviewPatchSerializer(data=request.data)
        s.is_valid(raise_exception=True)

        review.status = s.validated_data["status"]
        if review.status == ProductReview.StatusChoices.APPROVED:
            review.approved_at = review.approved_at or timezone.now()
        else:
            review.approved_at = None
        review.save(update_fields=["status", "approved_at"])

        return Response(ProductReviewSerializer(review).data, status=status.HTTP_200_OK)

    def delete(self, request, id, review_id):
        product = get_object_or_404(Product, id=id)
        review = get_object_or_404(ProductReview, id=review_id, product=product)
        review.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)