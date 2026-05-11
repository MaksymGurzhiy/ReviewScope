-- =====================================================
-- ReviewScope - Initial Database Schema
-- =====================================================
-- Run this in Supabase SQL Editor (Dashboard -> SQL Editor -> New query)
-- =====================================================

-- ----------------------------------------------------
-- Extensions
-- ----------------------------------------------------
create extension if not exists "uuid-ossp";
create extension if not exists "pgcrypto";

-- ----------------------------------------------------
-- profiles - extends auth.users with profile fields
-- ----------------------------------------------------
create table if not exists public.profiles (
    id uuid primary key references auth.users(id) on delete cascade,
    email text unique not null,
    full_name text,
    avatar_url text,
    plan text not null default 'free' check (plan in ('free', 'pro', 'enterprise')),
    api_key text unique,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_profiles_email on public.profiles(email);
create index if not exists idx_profiles_api_key on public.profiles(api_key);

-- ----------------------------------------------------
-- projects - business / company contexts
-- ----------------------------------------------------
create table if not exists public.projects (
    id uuid primary key default uuid_generate_v4(),
    user_id uuid not null references auth.users(id) on delete cascade,
    name text not null,
    description text,
    language text default 'auto',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_projects_user_id on public.projects(user_id);

-- ----------------------------------------------------
-- analyses - one record per uploaded file / run
-- ----------------------------------------------------
create table if not exists public.analyses (
    id uuid primary key default uuid_generate_v4(),
    project_id uuid not null references public.projects(id) on delete cascade,
    user_id uuid not null references auth.users(id) on delete cascade,
    file_name text not null,
    file_path text,
    file_size bigint,
    file_format text check (file_format in ('csv', 'xlsx', 'xls', 'json')),
    total_reviews int default 0,
    status text not null default 'pending' check (status in ('pending', 'processing', 'completed', 'failed')),
    error_message text,
    created_at timestamptz not null default now(),
    completed_at timestamptz,
    duration_ms int
);

create index if not exists idx_analyses_project_id on public.analyses(project_id);
create index if not exists idx_analyses_user_id on public.analyses(user_id);
create index if not exists idx_analyses_status on public.analyses(status);
create index if not exists idx_analyses_created_at on public.analyses(created_at desc);

-- ----------------------------------------------------
-- results - JSONB results of an analysis
-- ----------------------------------------------------
create table if not exists public.results (
    id uuid primary key default uuid_generate_v4(),
    analysis_id uuid not null unique references public.analyses(id) on delete cascade,
    sentiment_summary jsonb,
    aspects jsonb,
    topics jsonb,
    keywords jsonb,
    summary_text text,
    insights jsonb,
    recommendations jsonb,
    metrics jsonb,
    sample_reviews jsonb,
    created_at timestamptz not null default now()
);

create index if not exists idx_results_analysis_id on public.results(analysis_id);

-- ----------------------------------------------------
-- model_evaluations - LR vs BERT comparison records
-- ----------------------------------------------------
create table if not exists public.model_evaluations (
    id uuid primary key default uuid_generate_v4(),
    user_id uuid not null references auth.users(id) on delete cascade,
    dataset_name text not null,
    dataset_size int not null,
    model_name text not null,
    accuracy float,
    precision_score float,
    recall_score float,
    f1_score float,
    confusion_matrix jsonb,
    training_time_ms int,
    inference_time_ms int,
    created_at timestamptz not null default now()
);

create index if not exists idx_model_evals_user_id on public.model_evaluations(user_id);

-- ----------------------------------------------------
-- Auto-create profile on user signup
-- ----------------------------------------------------
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
    insert into public.profiles (id, email, full_name, api_key)
    values (
        new.id,
        new.email,
        coalesce(new.raw_user_meta_data->>'full_name', split_part(new.email, '@', 1)),
        encode(gen_random_bytes(32), 'hex')
    );
    return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
    after insert on auth.users
    for each row execute function public.handle_new_user();

-- ----------------------------------------------------
-- Auto-update updated_at timestamps
-- ----------------------------------------------------
create or replace function public.touch_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists profiles_touch_updated on public.profiles;
create trigger profiles_touch_updated
    before update on public.profiles
    for each row execute function public.touch_updated_at();

drop trigger if exists projects_touch_updated on public.projects;
create trigger projects_touch_updated
    before update on public.projects
    for each row execute function public.touch_updated_at();

-- ----------------------------------------------------
-- Row Level Security
-- ----------------------------------------------------
alter table public.profiles enable row level security;
alter table public.projects enable row level security;
alter table public.analyses enable row level security;
alter table public.results enable row level security;
alter table public.model_evaluations enable row level security;

-- ---- profiles policies ----
drop policy if exists "profiles_self_select" on public.profiles;
create policy "profiles_self_select" on public.profiles
    for select using (auth.uid() = id);

drop policy if exists "profiles_self_update" on public.profiles;
create policy "profiles_self_update" on public.profiles
    for update using (auth.uid() = id);

-- ---- projects policies ----
drop policy if exists "projects_owner_all" on public.projects;
create policy "projects_owner_all" on public.projects
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- ---- analyses policies ----
drop policy if exists "analyses_owner_all" on public.analyses;
create policy "analyses_owner_all" on public.analyses
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- ---- results policies ----
drop policy if exists "results_owner_all" on public.results;
create policy "results_owner_all" on public.results
    for all using (
        exists (
            select 1 from public.analyses a
            where a.id = analysis_id and a.user_id = auth.uid()
        )
    );

-- ---- model_evaluations policies ----
drop policy if exists "model_evals_owner_all" on public.model_evaluations;
create policy "model_evals_owner_all" on public.model_evaluations
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- ----------------------------------------------------
-- Storage: bucket for uploaded review files
-- ----------------------------------------------------
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
    'reviews',
    'reviews',
    false,
    52428800,  -- 50 MB
    array[
        'text/csv',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/json',
        'text/plain'
    ]
)
on conflict (id) do update
    set file_size_limit = excluded.file_size_limit,
        allowed_mime_types = excluded.allowed_mime_types;

-- ---- storage policies: each user works with their own folder ----
-- Files are stored as: reviews/<user_id>/<analysis_id>/<filename>

drop policy if exists "reviews_user_select" on storage.objects;
create policy "reviews_user_select" on storage.objects
    for select using (
        bucket_id = 'reviews'
        and (storage.foldername(name))[1] = auth.uid()::text
    );

drop policy if exists "reviews_user_insert" on storage.objects;
create policy "reviews_user_insert" on storage.objects
    for insert with check (
        bucket_id = 'reviews'
        and (storage.foldername(name))[1] = auth.uid()::text
    );

drop policy if exists "reviews_user_update" on storage.objects;
create policy "reviews_user_update" on storage.objects
    for update using (
        bucket_id = 'reviews'
        and (storage.foldername(name))[1] = auth.uid()::text
    );

drop policy if exists "reviews_user_delete" on storage.objects;
create policy "reviews_user_delete" on storage.objects
    for delete using (
        bucket_id = 'reviews'
        and (storage.foldername(name))[1] = auth.uid()::text
    );
