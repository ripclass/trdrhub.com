-- Enable RLS on normalized rules tables
alter table public.rules enable row level security;
alter table public.rules_audit enable row level security;

-- Service role bypass (used by FastAPI + CLI)
create policy rules_service_full_access on public.rules
    for all
    using (auth.role() = 'service_role')
    with check (auth.role() = 'service_role');

create policy rules_audit_service_access on public.rules_audit
    for select
    using (auth.role() = 'service_role');

-- Admin UI queries active rules
create policy rules_admin_read on public.rules
    for select
    using (
        auth.role() = 'authenticated'
        and exists (
            select 1
            from public.users u
            where u.id = auth.uid()
              and u.role in ('admin', 'super_admin')
        )
    );

create policy rules_admin_read_audit on public.rules_audit
    for select
    using (
        auth.role() = 'authenticated'
        and exists (
            select 1
            from public.users u
            where u.id = auth.uid()
              and u.role in ('admin', 'super_admin')
        )
    );

-- Optional limited read-only policy for tenants (success chips, etc.)
create policy rules_public_active on public.rules
    for select
    using (is_active = true);

