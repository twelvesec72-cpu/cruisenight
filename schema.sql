-- CruiseNight schema. Paste the whole file into Supabase > SQL Editor > Run, once.
-- Safe to re-run: everything is create-if-missing or replace.
--
-- Works with "Automatically expose new tables" on or off: every grant is explicit.
--
-- Security model (the anon key in the web page is public, so RLS + grants ARE the security):
--   * anon may INSERT an event, but only into columns that cannot publish it
--     (status / approved_at / skip_dates are not granted, so they take their defaults).
--   * anon may SELECT only approved rows, and only the public columns
--     (submitter_email is never granted). The app reads the public_events view.
--   * rsvps are never readable or writable directly; two SECURITY DEFINER
--     functions count and toggle them.
--   * Posters: anon may upload only under pending/ in the public "posters" bucket.
--   * Everything else needs a signed-in user listed in public.admins.

create extension if not exists pgcrypto;

-- ---------------------------------------------------------------- admins
create table if not exists public.admins (
  user_id uuid primary key references auth.users(id) on delete cascade
);
alter table public.admins enable row level security;
drop policy if exists "admins read self" on public.admins;
create policy "admins read self" on public.admins
  for select to authenticated using (user_id = auth.uid());
revoke all on public.admins from anon;
grant select on public.admins to authenticated;

create or replace function public.is_admin() returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.admins where user_id = auth.uid());
$$;
grant execute on function public.is_admin() to anon, authenticated;

-- ---------------------------------------------------------------- events
create table if not exists public.events (
  id             uuid primary key default gen_random_uuid(),
  status         text not null default 'pending'
                 check (status in ('pending','approved','rejected')),
  kind           text not null check (kind in ('cruise','show','meetup','swap')),
  title          text not null check (char_length(title) between 3 and 120),
  description    text check (char_length(description) <= 4000),
  start_at       timestamptz not null,
  end_at         timestamptz,
  recur_freq     text check (recur_freq in ('weekly','monthly')),
  recur_interval smallint not null default 1 check (recur_interval between 1 and 4),
  recur_byday    text check (recur_byday ~ '^(-1|[1-4])?(MO|TU|WE|TH|FR|SA|SU)$'),
  recur_until    date,
  skip_dates     date[] not null default '{}',
  venue_name     text check (char_length(venue_name) <= 120),
  address        text not null check (char_length(address) between 5 and 300),
  lat            double precision check (lat between -90 and 90),
  lng            double precision check (lng between -180 and 180),
  poster_path    text,
  entry_fee      text check (char_length(entry_fee) <= 60),
  contact_name   text check (char_length(contact_name) <= 80),
  contact_email  text check (char_length(contact_email) <= 120),
  contact_phone  text check (char_length(contact_phone) <= 40),
  website        text check (char_length(website) <= 300),
  facebook       text check (char_length(facebook) <= 300),
  instagram      text check (char_length(instagram) <= 300),
  tiktok         text check (char_length(tiktok) <= 300),
  submitter_email text not null check (char_length(submitter_email) between 5 and 120),
  created_at     timestamptz not null default now(),
  approved_at    timestamptz,
  check (end_at is null or end_at > start_at),
  check ((recur_freq is null) = (recur_byday is null))
);
create index if not exists events_status_start on public.events (status, start_at);
alter table public.events enable row level security;

-- Column grants: the real gate on what anon can write and read.
revoke all on public.events from anon;
-- Explicit, so this works whether or not the project auto-grants new tables.
-- RLS below still limits signed-in users to approved rows unless they are admins.
grant select, insert, update, delete on public.events to authenticated;
grant insert (id, kind, title, description, start_at, end_at,
              recur_freq, recur_interval, recur_byday, recur_until,
              venue_name, address, lat, lng, poster_path, entry_fee,
              contact_name, contact_email, contact_phone,
              website, facebook, instagram, tiktok, submitter_email)
  on public.events to anon;
grant select (id, status, kind, title, description, start_at, end_at,
              recur_freq, recur_interval, recur_byday, recur_until, skip_dates,
              venue_name, address, lat, lng, poster_path, entry_fee,
              contact_name, contact_email, contact_phone,
              website, facebook, instagram, tiktok, approved_at)
  on public.events to anon;

drop policy if exists "anon submit pending" on public.events;
create policy "anon submit pending" on public.events
  for insert to anon
  with check (status = 'pending'
              and approved_at is null
              and (poster_path is null or poster_path like 'pending/%'));

drop policy if exists "anyone reads approved" on public.events;
create policy "anyone reads approved" on public.events
  for select to anon, authenticated using (status = 'approved');

drop policy if exists "admin all" on public.events;
create policy "admin all" on public.events
  for all to authenticated using (public.is_admin()) with check (public.is_admin());

-- Flood guard: the queue cannot grow past 100 unreviewed submissions.
create or replace function public.events_queue_guard() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if not public.is_admin()
     and (select count(*) from public.events where status = 'pending') >= 100 then
    raise exception 'The approval queue is full. Please try again later.';
  end if;
  return new;
end $$;
drop trigger if exists events_queue_guard on public.events;
create trigger events_queue_guard before insert on public.events
  for each row execute function public.events_queue_guard();

-- What the app reads. security_invoker: the caller's grants and RLS apply,
-- so anon sees approved rows and public columns only.
create or replace view public.public_events with (security_invoker = true) as
  select id, kind, title, description, start_at, end_at,
         recur_freq, recur_interval, recur_byday, recur_until, skip_dates,
         venue_name, address, lat, lng, poster_path, entry_fee,
         contact_name, contact_email, contact_phone,
         website, facebook, instagram, tiktok
  from public.events
  where status = 'approved'
    and ( (recur_freq is not null and (recur_until is null or recur_until >= current_date))
       or coalesce(end_at, start_at) > now() - interval '12 hours');
grant select on public.public_events to anon, authenticated;

-- ---------------------------------------------------------------- "I'm going"
create table if not exists public.rsvps (
  event_id        uuid not null references public.events(id) on delete cascade,
  occurrence_date date not null,
  device_id       uuid not null,
  created_at      timestamptz not null default now(),
  primary key (event_id, occurrence_date, device_id)
);
alter table public.rsvps enable row level security;
revoke all on public.rsvps from anon, authenticated;

create or replace function public.set_going(p_event uuid, p_date date, p_device uuid, p_going boolean)
returns integer language plpgsql security definer set search_path = public as $$
declare n integer;
begin
  if not exists (select 1 from public.events where id = p_event and status = 'approved') then
    raise exception 'No such event';
  end if;
  if p_date < current_date - 1 or p_date > current_date + 400 then
    raise exception 'Date out of range';
  end if;
  if p_going then
    insert into public.rsvps (event_id, occurrence_date, device_id)
      values (p_event, p_date, p_device) on conflict do nothing;
  else
    delete from public.rsvps
      where event_id = p_event and occurrence_date = p_date and device_id = p_device;
  end if;
  select count(*) into n from public.rsvps where event_id = p_event and occurrence_date = p_date;
  return n;
end $$;

create or replace function public.going_counts()
returns table (event_id uuid, occurrence_date date, n integer)
language sql stable security definer set search_path = public as $$
  select r.event_id, r.occurrence_date, count(*)::int
  from public.rsvps r join public.events e on e.id = r.event_id
  where e.status = 'approved' and r.occurrence_date >= current_date - 1
  group by r.event_id, r.occurrence_date;
$$;

revoke all on function public.set_going(uuid, date, uuid, boolean) from public;
revoke all on function public.going_counts() from public;
grant execute on function public.set_going(uuid, date, uuid, boolean) to anon, authenticated;
grant execute on function public.going_counts() to anon, authenticated;

-- ---------------------------------------------------------------- posters
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('posters', 'posters', true, 5242880, array['image/jpeg','image/png','image/webp'])
on conflict (id) do update
  set public = excluded.public,
      file_size_limit = excluded.file_size_limit,
      allowed_mime_types = excluded.allowed_mime_types;

drop policy if exists "anon upload pending posters" on storage.objects;
create policy "anon upload pending posters" on storage.objects
  for insert to anon
  with check (bucket_id = 'posters' and (storage.foldername(name))[1] = 'pending');

drop policy if exists "admin manage posters" on storage.objects;
create policy "admin manage posters" on storage.objects
  for all to authenticated
  using (bucket_id = 'posters' and public.is_admin())
  with check (bucket_id = 'posters' and public.is_admin());

-- ---------------------------------------------------------------- make yourself admin
-- After creating your user under Authentication > Users, run (with your email):
--   insert into public.admins (user_id)
--   select id from auth.users where email = 'you@example.com';
