create table public.profiles (
    id uuid primary key default gen_random_uuid(),
    auth_user_id uuid unique references auth.users (id) on delete cascade,
    username text not null unique check (username ~ '^[a-z0-9][a-z0-9-]{2,31}$'),
    display_name text not null,
    bio text not null default '',
    location text not null default '',
    contact_email text not null,
    created_at timestamptz not null default now()
);

create table public.cards (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references public.profiles (id) on delete cascade,
    name text not null,
    set_name text not null,
    collector_number text not null,
    condition text not null,
    finish text not null,
    price_clp integer not null check (price_clp >= 0),
    image_url text not null,
    status text not null default 'available' check (status in ('available', 'reserved', 'sold')),
    created_at timestamptz not null default now()
);

create index cards_user_id_idx on public.cards (user_id);
create index cards_public_catalog_idx on public.cards (user_id, status, created_at desc);

alter table public.profiles enable row level security;
alter table public.cards enable row level security;

create policy "Public profiles are readable"
    on public.profiles for select
    using (true);

create policy "Users can create their profile"
    on public.profiles for insert to authenticated
    with check (auth_user_id = auth.uid());

create policy "Users can update their profile"
    on public.profiles for update to authenticated
    using (auth_user_id = auth.uid())
    with check (auth_user_id = auth.uid());

create policy "Users can delete their profile"
    on public.profiles for delete to authenticated
    using (auth_user_id = auth.uid());

create policy "Available cards are publicly readable"
    on public.cards for select
    using (status = 'available');

create policy "Users can insert their cards"
    on public.cards for insert to authenticated
    with check (
        exists (
            select 1 from public.profiles
            where id = user_id and auth_user_id = auth.uid()
        )
    );

create policy "Users can read all their cards"
    on public.cards for select to authenticated
    using (
        exists (
            select 1 from public.profiles
            where id = user_id and auth_user_id = auth.uid()
        )
    );

create policy "Users can update their cards"
    on public.cards for update to authenticated
    using (
        exists (
            select 1 from public.profiles
            where id = user_id and auth_user_id = auth.uid()
        )
    )
    with check (
        exists (
            select 1 from public.profiles
            where id = user_id and auth_user_id = auth.uid()
        )
    );

create policy "Users can delete their cards"
    on public.cards for delete to authenticated
    using (
        exists (
            select 1 from public.profiles
            where id = user_id and auth_user_id = auth.uid()
        )
    );
