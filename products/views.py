# products/views.py
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser

from products.models import Category, Product, ProductReview, ProductImage
from products.permissions import IsAdmin
from products.serializers import (
    CategorySerializer,
    ProductSerializer,
    AdminProductWriteSerializer,
    ProductReviewSerializer,
    AdminReviewPatchSerializer,
    ProductImageSerializer,
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
            Product.objects.select_related("category", "seo", "dimensions")
            .prefetch_related("images", "specs", "reviews__author")
            .all()
        )


class AdminProductsView(generics.ListCreateAPIView):
    """
    Admin list and create products.

    Methods:
      - GET: list products
      - POST: create a product

    Auth:
      - Requires: Authorization: Bearer <access_token>
      - Requires: is_admin == True

    Notes on images (Gallery workflow):
      - Product images are stored in the ProductImage gallery.
      - When creating/updating a product you DO NOT upload images here.
      - You attach existing gallery images by providing their IDs under "images".
      - If "images" is omitted: product images are NOT changed.
      - If "images" is []: product images will be cleared.
      - If "images" is provided (non-empty): it will replace the product images (M2M set).

    GET query params:
      - q: string (search by title/slug/sku/brand)
      - category: string (category slug)
      - inStock: true|false|1|0

    POST input (JSON):
      - slug: string (unique, required)
      - title: string (required)
      - shortDescription: string (required)
      - description: string (optional, nullable)
      - sku: string (optional, nullable)
      - brand: string (optional, nullable)
      - categorySlug: string (required)
      - priceToman: int (required)
      - compareAtPriceToman: int (optional, nullable)
      - inStock: bool (required)
      - stockQuantity: int (optional, nullable)
      - rating: number/string (optional, nullable)

      Optional nested:
      - images: list[{id: UUID}]
        Example:
          "images": [{"id": "<product_image_uuid>"}, {"id": "<product_image_uuid>"}]

      - specs: list[{key: string, value: string}]
        Note: keys must be unique per product.

      - seo: {title?: string, description?: string, canonical?: url} | null

      - dimensions: {lengthMm?: int, widthMm?: int, heightMm?: int} | null

    Responses:
      - 200 OK: list products (ProductSerializer)
      - 201 Created: created product (ProductSerializer)
      - 400 Bad Request: validation error
      - 401 Unauthorized: missing/invalid token
      - 403 Forbidden: not admin
    """

    permission_classes = (IsAdmin,)
    queryset = (
        Product.objects.select_related("category", "seo", "dimensions")
        .prefetch_related("images", "specs", "reviews__author")
        .all()
        .order_by("-created_at")
    )

    def get_serializer_class(self):
        if self.request.method == "POST":
            return AdminProductWriteSerializer
        return ProductSerializer

    def create(self, request, *args, **kwargs):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        product = s.save()
        return Response(ProductSerializer(product).data, status=status.HTTP_201_CREATED)


class AdminProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Admin retrieve, update, and delete a product.

    Methods:
      - GET: retrieve product (ProductSerializer)
      - PATCH/PUT: update product (AdminProductWriteSerializer input, ProductSerializer output)
      - DELETE: delete product

    Auth:
      - Requires: Authorization: Bearer <access_token>
      - Requires: is_admin == True

    URL params:
      - id: string (UUID)

    PATCH/PUT input (JSON):
      Same fields as create are accepted. Partial update is allowed for PATCH.

      Images behavior (M2M to gallery):
      - If "images" is omitted: images are NOT changed.
      - If "images" is []: all images will be cleared (product.images.set([])).
      - If "images" is provided: it replaces the product's images (product.images.set([...])).
      - This endpoint does NOT upload image files; use the gallery endpoints to upload first.

      Specs behavior:
      - If "specs" is omitted: specs are NOT changed.
      - If "specs" is present: existing specs will be replaced (delete + recreate).
        Note: spec keys must be unique per product.

      SEO behavior:
      - If "seo" is omitted: seo is NOT changed.
      - If "seo" is null: seo row will be deleted.
      - If "seo" is an object: update_or_create will be used.

      Dimensions behavior:
      - If "dimensions" is omitted: dimensions are NOT changed.
      - If "dimensions" is null: dimensions row will be deleted.
      - If "dimensions" is an object: update_or_create will be used.

    Responses:
      - 200 OK: product returned/updated (ProductSerializer)
      - 204 No Content: product deleted
      - 400 Bad Request: validation error
      - 401 Unauthorized: missing/invalid token
      - 403 Forbidden: not admin
      - 404 Not Found: product not found
    """

    permission_classes = (IsAdmin,)
    queryset = (
        Product.objects.select_related("category", "seo", "dimensions")
        .prefetch_related("images", "specs", "reviews__author")
        .all()
    )
    lookup_field = "id"

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return AdminProductWriteSerializer
        return ProductSerializer

    def update(self, request, *args, **kwargs):
        partial = request.method == "PATCH"
        instance = self.get_object()

        s = self.get_serializer(instance, data=request.data, partial=partial)
        s.is_valid(raise_exception=True)
        product = s.save()

        return Response(ProductSerializer(product).data, status=status.HTTP_200_OK)


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


class AdminCategoriesView(generics.ListCreateAPIView):
    """
    Admin list and create categories.

    Methods:
      - GET: list categories
      - POST: create category

    Auth:
      - Requires: Authorization: Bearer <access_token>
      - Requires: is_admin == True

    GET query params:
      - q: string (search in title/slug)

    POST input (JSON):
      - slug: string (unique)
      - title: string

    Responses:
      - 200 OK: list categories
      - 201 Created: created category
      - 400 Bad Request: validation error
      - 401 Unauthorized: missing/invalid token
      - 403 Forbidden: not admin
    """
    permission_classes = (IsAdmin,)
    serializer_class = CategorySerializer
    queryset = Category.objects.all().order_by("title")

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(slug__icontains=q))
        return qs


class AdminCategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Admin retrieve, update, and delete a category.

    Methods:
      - GET: retrieve category
      - PATCH/PUT: update category
      - DELETE: delete category

    Auth:
      - Requires: Authorization: Bearer <access_token>
      - Requires: is_admin == True

    URL params:
      - id: string (UUID)

    PATCH/PUT input (JSON):
      - slug: string (unique)
      - title: string

    Responses:
      - 200 OK: category returned/updated
      - 204 No Content: category deleted
      - 400 Bad Request: validation error
      - 401 Unauthorized: missing/invalid token
      - 403 Forbidden: not admin
      - 404 Not Found: category not found

    Notes:
      - Deleting a category that is referenced by products may fail because Product.category uses PROTECT.
    """
    permission_classes = (IsAdmin,)
    serializer_class = CategorySerializer
    queryset = Category.objects.all()
    lookup_field = "id"


class AdminProductImagesView(generics.ListCreateAPIView):
    """
       Admin list and upload product images (gallery).

       Methods:
         - GET: list images in gallery
         - POST: upload a new image to gallery

       Auth:
         - Requires: Authorization: Bearer <access_token>
         - Requires: is_admin == True

       GET query params:
         - q: string (search in alt)

       POST input (multipart/form-data):
         - src: file (required)
         - alt: string (optional, nullable)
         - width: int (optional)   # only if you want to send manually; otherwise leave empty
         - height: int (optional)  # only if you want to send manually; otherwise leave empty

       Notes:
         - This endpoint returns the ProductImage "id". Use that id when attaching images to products.

       Responses:
         - 200 OK: list images
         - 201 Created: created image
         - 400 Bad Request: validation error
         - 401 Unauthorized: missing/invalid token
         - 403 Forbidden: not admin
       """
    permission_classes = (IsAdmin,)
    serializer_class = ProductImageSerializer
    queryset = ProductImage.objects.all().order_by("-id")
    parser_classes = (MultiPartParser, FormParser)

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(alt__icontains=q)
        return qs


class AdminProductImageDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Admin retrieve, update, and delete a product image (gallery item).

    Methods:
      - GET: retrieve image
      - PATCH/PUT: update image fields
      - DELETE: delete image

    Auth:
      - Requires: Authorization: Bearer <access_token>
      - Requires: is_admin == True

    URL params:
      - id: string (UUID)

    PATCH/PUT input:
      - Accepts multipart/form-data (for src file) and normal form fields:
        - src: file (optional)
        - alt: string (optional, nullable)
        - width: int (optional, nullable)
        - height: int (optional, nullable)

    Notes:
      - If an image is linked to products, deleting it will remove the M2M relationships as well.

    Responses:
      - 200 OK: image returned/updated
      - 204 No Content: image deleted
      - 400 Bad Request: validation error
      - 401 Unauthorized: missing/invalid token
      - 403 Forbidden: not admin
      - 404 Not Found: image not found
    """
    permission_classes = (IsAdmin,)
    serializer_class = ProductImageSerializer
    queryset = ProductImage.objects.all()
    lookup_field = "id"
    parser_classes = (MultiPartParser, FormParser)
