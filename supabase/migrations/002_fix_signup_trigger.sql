-- =====================================================
-- Fix: "Database error saving new user" on sign-up
-- =====================================================
-- В Supabase триггер on_auth_user_created выполняется под ролью
-- supabase_auth_admin. По умолчанию у этой роли нет прав на таблицы
-- в public-схеме, поэтому INSERT в public.profiles падает.
-- =====================================================

-- 1) Грантим доступ роли supabase_auth_admin
grant usage on schema public to supabase_auth_admin;
grant insert, select, update on public.profiles to supabase_auth_admin;

-- 2) Делаем функцию устойчивой к ошибкам (если что-то пошло не так -
-- регистрация всё равно завершается, в логах будет warning)
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public, pg_temp
as $$
begin
    insert into public.profiles (id, email, full_name, api_key)
    values (
        new.id,
        new.email,
        coalesce(new.raw_user_meta_data->>'full_name', split_part(new.email, '@', 1)),
        encode(gen_random_bytes(32), 'hex')
    )
    on conflict (id) do nothing;
    return new;
exception when others then
    raise warning 'handle_new_user failed for %: %', new.id, sqlerrm;
    return new;
end;
$$;

-- 3) Добавляем INSERT-политику, чтобы триггер мог отрабатывать,
--    если он запускается от auth.uid() (на всякий случай).
drop policy if exists "profiles_insert_self" on public.profiles;
create policy "profiles_insert_self" on public.profiles
    for insert with check (auth.uid() = id or auth.uid() is null);
