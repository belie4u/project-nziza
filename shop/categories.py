# from oscar.apps.catalogue.categories import create_from_breadcrumbs
#
# categories = [
#     'Hospitality > Polos',
#     'Hospitality > Shirts & Blouses',
#     'Hospitality > Chefswear',
#     'Sustainable & Organic'
#
#
#     ]
#
# for breadcrumb in categories:
#     create_from_breadcrumbs(breadcrumb)
#
# print('Built Categories.')


from oscar.apps.catalogue.categories import create_from_breadcrumbs

categories = [
    'Polos',
    'Knitwear',
    'Shorts & Trousers',
    'T-Shirts',
    'Kids Fashion',
    'Sweatpants',
    'Sweatshirts',
    'Hoodies',
    'Bags',
    'Hospitality',
    'Headwear',
    'Shirts & Blouses',
    'Featured Products',
    'Technical Jackets',
    'Fashion Jackets',
    'Softshell Jackets',
    'Chefswear',
    'Health & Beauty',
    'Workwear',
    'Safetywear',
    'Fleece Jackets',
    'Towels',
    'Sustainable & Organic',
    'Golf',
    'Uncategorized',
    'Wolf Laundry',
    'Relish Doncaster'
]

for category in categories:
    create_from_breadcrumbs(category)

print('Built Categories.')
