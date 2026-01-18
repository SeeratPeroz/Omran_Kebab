from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from FoodOrdering.models import (
    Category,
    Product,
    OptionGroup,
    Option,
    ProductOptionGroup,
)


class Command(BaseCommand):
    help = "Seed Omran Kebap menu + basic option groups (placeholder choices)."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Seeding Omran menu..."))

        # -------------------------
        # 1) Categories
        # -------------------------
        categories_data = [
            ("DÖNER", 10),
            ("SPEZIALITÄTEN", 20),
            ("VEGETARISCH", 30),
            ("BEILAGEN", 40),
            ("SOẞEN", 50),
            ("ALKOHOLFREIE GETRÄNKE", 60),
        ]

        categories = {}
        for name, sort_order in categories_data:
            cat, _ = Category.objects.get_or_create(
                slug=slugify(name),
                defaults={"name": name, "is_active": True, "sort_order": sort_order},
            )
            # keep name/sort updated if you re-run seed
            cat.name = name
            cat.sort_order = sort_order
            cat.is_active = True
            cat.save()
            categories[name] = cat

        # -------------------------
        # 2) Products (name, price, category)
        # -------------------------
        products_data = [
            # DÖNER
            ("Döner-Kebab", "6.50", "DÖNER"),
            ("Döner-Box", "8.00", "DÖNER"),
            ("Dürüm", "7.50", "DÖNER"),
            ("Dürüm mit Käse", "9.00", "DÖNER"),
            ("Döner-Teller mit Salat", "10.00", "DÖNER"),
            ("Döner-Teller mit Pommes Frites & Salat", "12.00", "DÖNER"),
            ("Döner-Teller mit Reis & Salat", "12.00", "DÖNER"),
            ("Hähnchen-Döner", "5.00", "DÖNER"),
            ("Big-Hähnchen-Döner", "7.50", "DÖNER"),
            ("Hähnchen-Box mit Pommes Frites", "5.00", "DÖNER"),
            ("Hähnchen-Dürüm", "6.00", "DÖNER"),
            ("Hähnchen-Teller mit Salat", "5.00", "DÖNER"),
            ("Hähnchen-Teller mit Pommes Frites & Salat", "9.50", "DÖNER"),
            ("Hähnchen-Teller mit Reis & Salat", "7.00", "DÖNER"),
            ("Lahmacun", "9.00", "DÖNER"),

            # SPEZIALITÄTEN
            ("Tschelo Kubideh", "18.00", "SPEZIALITÄTEN"),
            ("Tschelo Tschendje", "15.00", "SPEZIALITÄTEN"),
            ("Soltani Kebab", "15.00", "SPEZIALITÄTEN"),
            ("Djudjeh Kebap", "14.00", "SPEZIALITÄTEN"),
            ("Djudjeh be Ostkokhan", "14.00", "SPEZIALITÄTEN"),
            ("Sereshk Polo", "18.00", "SPEZIALITÄTEN"),

            # VEGETARISCH
            ("Vegetarischer Döner mit Halloumi", "7.00", "VEGETARISCH"),
            ("Vegetarischer Döner mit Halloumi & Falafel", "8.00", "VEGETARISCH"),
            ("Vegetarischer Dürüm mit Halloumi", "7.00", "VEGETARISCH"),
            ("Vegetarischer Dürüm mit Halloumi & Falafel", "8.00", "VEGETARISCH"),
            ("Vegetarischer Teller mit Halloumi, Pommes Frites & Salat", "12.00", "VEGETARISCH"),
            ("Vegetarischer Teller mit Halloumi, Falafel & Salat", "14.00", "VEGETARISCH"),
            ("Vegetarischer Teller mit Reis, Halloumi & Salat", "12.00", "VEGETARISCH"),

            # BEILAGEN
            ("Nudeln mit Käse", "8.00", "BEILAGEN"),
            ("Pommes frites", "3.50", "BEILAGEN"),

            # SOẞEN (sold as separate items)
            ("17 ml Heinz Ketchup", "0.50", "SOẞEN"),
            ("17 ml Heinz Mayonnaise", "0.50", "SOẞEN"),

            # ALKOHOLFREIE GETRÄNKE
            ("Apollinaris Classic 0,5 l", "0.85", "ALKOHOLFREIE GETRÄNKE"),
            ("Coca-Cola® 1,0 l", "2.85", "ALKOHOLFREIE GETRÄNKE"),
            ("Coca-Cola® 0,33 l", "2.25", "ALKOHOLFREIE GETRÄNKE"),
            ("Fanta 1,0 l", "2.85", "ALKOHOLFREIE GETRÄNKE"),
            ("Fanta 0,33 l", "2.25", "ALKOHOLFREIE GETRÄNKE"),
            ("Fanta Exotic 0,33 l", "2.00", "ALKOHOLFREIE GETRÄNKE"),
            ("Club Mate 0,5 l", "2.35", "ALKOHOLFREIE GETRÄNKE"),
            ("Mio Mio Mate Original 0,5 l", "3.50", "ALKOHOLFREIE GETRÄNKE"),
        ]

        products = {}
        for name, price, cat_name in products_data:
            slug = slugify(name)
            prod, _ = Product.objects.get_or_create(
                slug=slug,
                defaults={
                    "category": categories[cat_name],
                    "name": name,
                    "description": "",
                    "price": Decimal(price),
                    "is_available": True,
                },
            )
            # keep updated on re-run
            prod.category = categories[cat_name]
            prod.name = name
            prod.price = Decimal(price)
            prod.is_available = True
            prod.save()
            products[name] = prod

        # -------------------------
        # 3) OptionGroups (max 1)
        # -------------------------
        sauce_group = self._get_or_create_group(
            name="Soße deiner Wahl",
            slug="sosse-deiner-wahl",
            is_required=True,
            min_select=1,
            max_select=1,
            sort_order=10,
        )

        cheese_group = self._get_or_create_group(
            name="Käse deiner Wahl",
            slug="kase-deiner-wahl",
            is_required=True,
            min_select=1,
            max_select=1,
            sort_order=20,
        )

        portion_group = self._get_or_create_group(
            name="Portion deiner Wahl",
            slug="portion-deiner-wahl",
            is_required=True,
            min_select=1,
            max_select=1,
            sort_order=30,
        )

        # -------------------------
        # 4) Options (placeholders)
        # -------------------------
        self._seed_options(
            sauce_group,
            [
                ("Knoblauch", "0.00"),
                ("Kräuter", "0.00"),
                ("Scharf", "0.00"),
            ],
        )

        self._seed_options(
            cheese_group,
            [
                ("Gouda", "0.00"),
                ("Feta", "0.50"),
                ("Halloumi", "1.00"),
            ],
        )

        self._seed_options(
            portion_group,
            [
                ("Klein", "0.00"),
                ("Mittel", "1.00"),
                ("Groß", "2.00"),
            ],
        )

        # -------------------------
        # 5) Attach groups to products
        # -------------------------
        # Rule from you: max 1 (already in group). Apply Sauce to all DÖNER + VEGETARISCH products.
        donor_names = [name for name, _, cat in products_data if cat == "DÖNER"]
        veg_names = [name for name, _, cat in products_data if cat == "VEGETARISCH"]

        for pname in donor_names + veg_names:
            self._attach_group(products[pname], sauce_group, sort_order=10)

        # "Dürüm mit Käse" additionally gets cheese choice
        self._attach_group(products["Dürüm mit Käse"], cheese_group, sort_order=20)

        # Pommes frites gets portion choice
        self._attach_group(products["Pommes frites"], portion_group, sort_order=30)

        self.stdout.write(self.style.SUCCESS("✅ Omran menu seeded successfully!"))

    # -------------------------
    # helpers
    # -------------------------
    def _get_or_create_group(self, name, slug, is_required, min_select, max_select, sort_order):
        grp, _ = OptionGroup.objects.get_or_create(
            slug=slug,
            defaults={
                "name": name,
                "is_required": is_required,
                "min_select": min_select,
                "max_select": max_select,
                "sort_order": sort_order,
                "is_active": True,
            },
        )
        grp.name = name
        grp.is_required = is_required
        grp.min_select = min_select
        grp.max_select = max_select
        grp.sort_order = sort_order
        grp.is_active = True
        grp.save()
        return grp

    def _seed_options(self, group, options_list):
        # options_list: [(name, price_delta), ...]
        for idx, (name, price_delta) in enumerate(options_list, start=1):
            opt, _ = Option.objects.get_or_create(
                group=group,
                name=name,
                defaults={
                    "price_delta": Decimal(price_delta),
                    "sort_order": idx,
                    "is_active": True,
                },
            )
            opt.price_delta = Decimal(price_delta)
            opt.sort_order = idx
            opt.is_active = True
            opt.save()

    def _attach_group(self, product, group, sort_order=0):
        pog, _ = ProductOptionGroup.objects.get_or_create(
            product=product,
            group=group,
            defaults={"sort_order": sort_order},
        )
        pog.sort_order = sort_order
        # keep overrides empty (use group defaults)
        pog.is_required = None
        pog.min_select = None
        pog.max_select = None
        pog.save()
