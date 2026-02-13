from rest_framework import serializers
from products.models import (
    Category,
    Product,
    ProductImage,
    ProductSpec,
    ProductSeo,
    ProductDimensions,
    ProductReview,
)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "slug", "title")


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ("id", "alt", "src", "width", "height")


class ProductSpecSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductSpec
        fields = ("key", "value")


class ProductReviewSerializer(serializers.ModelSerializer):
    authorName = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    approvedAt = serializers.DateTimeField(source="approved_at", read_only=True)

    class Meta:
        model = ProductReview
        fields = (
            "id",
            "authorName",
            "rating",
            "title",
            "body",
            "createdAt",
            "status",
            "approvedAt",
        )

    def get_authorName(self, obj):
        if not obj.author_id:
            return None
        full = (getattr(obj.author, "full_name", "") or "").strip()
        if full:
            return full
        first = (getattr(obj.author, "first_name", "") or "").strip()
        last = (getattr(obj.author, "last_name", "") or "").strip()
        name = f"{first} {last}".strip()
        return name or getattr(obj.author, "phone", None)


class ProductSeoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductSeo
        fields = ("title", "description", "canonical")


class ProductDimensionsSerializer(serializers.ModelSerializer):
    lengthMm = serializers.IntegerField(source="length_mm", required=False, allow_null=True)
    widthMm = serializers.IntegerField(source="width_mm", required=False, allow_null=True)
    heightMm = serializers.IntegerField(source="height_mm", required=False, allow_null=True)

    class Meta:
        model = ProductDimensions
        fields = ("lengthMm", "widthMm", "heightMm")


class ProductSerializer(serializers.ModelSerializer):
    shortDescription = serializers.CharField(source="short_description")
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    categorySlug = serializers.SlugField(source="category.slug", read_only=True)

    priceToman = serializers.IntegerField(source="price_toman")
    compareAtPriceToman = serializers.IntegerField(source="compare_at_price_toman", required=False, allow_null=True)

    inStock = serializers.BooleanField(source="in_stock")
    stockQuantity = serializers.IntegerField(source="stock_quantity", required=False, allow_null=True)

    images = ProductImageSerializer(many=True, read_only=True)
    specs = ProductSpecSerializer(many=True, read_only=True)

    rating = serializers.DecimalField(max_digits=3, decimal_places=2, required=False, allow_null=True)

    seo = ProductSeoSerializer(read_only=True)
    dimensions = ProductDimensionsSerializer(read_only=True)
    reviews = ProductReviewSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "slug",
            "title",
            "shortDescription",
            "description",
            "createdAt",
            "updatedAt",
            "sku",
            "brand",
            "categorySlug",
            "priceToman",
            "compareAtPriceToman",
            "inStock",
            "stockQuantity",
            "rating",
            "images",
            "specs",
            "seo",
            "dimensions",
            "reviews",
        )


class AdminProductWriteSerializer(serializers.ModelSerializer):
    shortDescription = serializers.CharField(source="short_description")
    categorySlug = serializers.SlugField(write_only=True)
    priceToman = serializers.IntegerField(source="price_toman")
    compareAtPriceToman = serializers.IntegerField(
        source="compare_at_price_toman",
        required=False,
        allow_null=True,
    )
    inStock = serializers.BooleanField(source="in_stock")
    stockQuantity = serializers.IntegerField(source="stock_quantity", required=False, allow_null=True)

    class Meta:
        model = Product
        fields = (
            "id",
            "slug",
            "title",
            "shortDescription",
            "description",
            "sku",
            "brand",
            "categorySlug",
            "priceToman",
            "compareAtPriceToman",
            "inStock",
            "stockQuantity",
            "rating",
        )

    def validate_categorySlug(self, value):
        if not Category.objects.filter(slug=value).exists():
            raise serializers.ValidationError("Category not found.")
        return value

    def create(self, validated_data):
        category_slug = validated_data.pop("categorySlug")
        category = Category.objects.get(slug=category_slug)
        validated_data["category"] = category
        return super().create(validated_data)

    def update(self, instance, validated_data):
        category_slug = validated_data.pop("categorySlug", None)
        if category_slug is not None:
            instance.category = Category.objects.get(slug=category_slug)
        return super().update(instance, validated_data)


class AdminReviewPatchSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=ProductReview.StatusChoices.choices)