insert into public.profiles (
    id, username, display_name, bio, location, contact_email
) values (
    '00000000-0000-4000-8000-000000000001',
    'erwin',
    'Erwin',
    'Coleccionista de cartas clásicas. Precios en CLP y retiro o envío por conversar.',
    'Santiago, Chile',
    'coleccionista@example.com'
) on conflict (username) do nothing;

with demo_cards (
    id, name, set_name, collector_number, condition, finish, price_clp, image_url
) as (
    values
        ('00000000-0000-4000-8000-000000000101'::uuid, 'Charizard', 'Base Set', '4/102', 'Casi nueva', 'Holo', 95000, 'https://assets.tcgdex.net/en/base/base1/4/high.png'),
        ('00000000-0000-4000-8000-000000000102'::uuid, 'Pikachu', 'Base Set', '58/102', 'Excelente', 'Normal', 12000, 'https://assets.tcgdex.net/en/base/base1/58/high.png'),
        ('00000000-0000-4000-8000-000000000103'::uuid, 'Blastoise', 'Base Set', '2/102', 'Excelente', 'Holo', 42000, 'https://assets.tcgdex.net/en/base/base1/2/high.png'),
        ('00000000-0000-4000-8000-000000000104'::uuid, 'Venusaur', 'Base Set', '15/102', 'Jugada', 'Holo', 28000, 'https://assets.tcgdex.net/en/base/base1/15/high.png'),
        ('00000000-0000-4000-8000-000000000105'::uuid, 'Mewtwo', 'Base Set', '10/102', 'Casi nueva', 'Holo', 35000, 'https://assets.tcgdex.net/en/base/base1/10/high.png'),
        ('00000000-0000-4000-8000-000000000106'::uuid, 'Zapdos', 'Base Set', '16/102', 'Excelente', 'Holo', 24000, 'https://assets.tcgdex.net/en/base/base1/16/high.png'),
        ('00000000-0000-4000-8000-000000000107'::uuid, 'Hitmonchan', 'Base Set', '7/102', 'Jugada', 'Holo', 9500, 'https://assets.tcgdex.net/en/base/base1/7/high.png'),
        ('00000000-0000-4000-8000-000000000108'::uuid, 'Machamp', 'Base Set', '8/102', 'Excelente', 'Holo', 11000, 'https://assets.tcgdex.net/en/base/base1/8/high.png')
)
insert into public.cards (
    id, user_id, name, set_name, collector_number, condition, finish, price_clp, image_url
)
select
    id, '00000000-0000-4000-8000-000000000001', name, set_name,
    collector_number, condition, finish, price_clp, image_url
from demo_cards
on conflict (id) do nothing;
