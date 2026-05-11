-- Add live progress columns so the UI can show pipeline stages while
-- analyses are running. Both columns are optional (defaults are safe).

alter table public.analyses
  add column if not exists progress_stage text,
  add column if not exists progress_pct integer not null default 0;
