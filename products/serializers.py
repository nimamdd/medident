from django.db import transaction
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
    id = serializers.UUIDField(read_only=True)

    class Meta:
        model = ProductImage
        fields = ("id", "alt", "src", "width", "height", "position")


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

    images = ProductImageSerializer(many=True, required=False)
    specs = ProductSpecSerializer(many=True, required=False)
    seo = ProductSeoSerializer(required=False, allow_null=True)
    dimensions = ProductDimensionsSerializer(required=False, allow_null=True)

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
            "images",
            "specs",
            "seo",
            "dimensions",
        )

    def validate_categorySlug(self, value):
        if not Category.objects.filter(slug=value).exists():
            raise serializers.ValidationError("Category not found.")
        return value

    def validate_specs(self, value):
        seen = set()
        dup = set()
        for item in value:
            k = item.get("key")
            if not k:
                continue
            if k in seen:
                dup.add(k)
            seen.add(k)
        if dup:
            raise serializers.ValidationError(f"Duplicate spec key(s): {', '.join(sorted(dup))}")
        return value

    @transaction.atomic
    def create(self, validated_data):
        category_slug = validated_data.pop("categorySlug")

        images_data = validated_data.pop("images", [])
        specs_data = validated_data.pop("specs", [])
        seo_data = validated_data.pop("seo", None)
        dimensions_data = validated_data.pop("dimensions", None)

        validated_data["category"] = Category.objects.get(slug=category_slug)
        product = Product.objects.create(**validated_data)

        if images_data:
            ProductImage.objects.bulk_create(
                [ProductImage(product=product, **img) for img in images_data]
            )

        if specs_data:
            ProductSpec.objects.bulk_create(
                [ProductSpec(product=product, **sp) for sp in specs_data]
            )

        if seo_data:
            ProductSeo.objects.create(product=product, **seo_data)

        if dimensions_data:
            ProductDimensions.objects.create(product=product, **dimensions_data)

        return product

    @transaction.atomic
    def update(self, instance, validated_data):
        category_slug = validated_data.pop("categorySlug", None)

        images_data = validated_data.pop("images", None)
        specs_data = validated_data.pop("specs", None)
        seo_data = validated_data.pop("seo", None)
        dimensions_data = validated_data.pop("dimensions", None)

        if category_slug is not None:
            instance.category = Category.objects.get(slug=category_slug)

        instance = super().update(instance, validated_data)

        if images_data is not None:
            instance.images.all().delete()
            if images_data:
                ProductImage.objects.bulk_create(
                    [ProductImage(product=instance, **img) for img in images_data]
                )

        if specs_data is not None:
            instance.specs.all().delete()
            if specs_data:
                ProductSpec.objects.bulk_create(
                    [ProductSpec(product=instance, **sp) for sp in specs_data]
                )

        if seo_data is not None:
            if seo_data is None:
                ProductSeo.objects.filter(product=instance).delete()
            else:
                ProductSeo.objects.update_or_create(product=instance, defaults=seo_data)

        if dimensions_data is not None:
            if dimensions_data is None:
                ProductDimensions.objects.filter(product=instance).delete()
            else:
                ProductDimensions.objects.update_or_create(product=instance, defaults=dimensions_data)

        return instance


class AdminReviewPatchSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=ProductReview.StatusChoices.choices)
