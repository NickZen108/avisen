begin;

-- Cover foreign keys used by moderation/admin workflows.
create index if not exists audit_log_actor_idx on public.audit_log(actor_id);
create index if not exists media_owner_idx on public.media(owner_id);
create index if not exists media_submission_idx on public.media(submission_id);
create index if not exists publish_requests_requested_by_idx on public.publish_requests(requested_by);
create index if not exists publish_requests_submission_idx on public.publish_requests(submission_id);
create index if not exists submission_revisions_created_by_idx on public.submission_revisions(created_by);
create index if not exists user_roles_granted_by_idx on public.user_roles(granted_by);

-- Cache auth/role checks once per statement instead of recalculating per row.
drop policy if exists profiles_self_read on public.profiles;
create policy profiles_self_read on public.profiles for select using (user_id = (select auth.uid()) or (select private.has_role('editor')) or (select private.has_role('admin')));
drop policy if exists profiles_self_update on public.profiles;
create policy profiles_self_update on public.profiles for update using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));

drop policy if exists roles_self_read on public.user_roles;
create policy roles_self_read on public.user_roles for select using (user_id = (select auth.uid()) or (select private.has_role('admin')));

drop policy if exists submissions_author_read on public.submissions;
create policy submissions_author_read on public.submissions for select using (author_id = (select auth.uid()) or (select private.has_role('editor')) or (select private.has_role('admin')));
drop policy if exists submissions_author_insert on public.submissions;
create policy submissions_author_insert on public.submissions for insert with check (author_id = (select auth.uid()) and (select private.has_role('chronicler')));
drop policy if exists submissions_author_update on public.submissions;
create policy submissions_author_update on public.submissions for update using (author_id = (select auth.uid()) and (select private.has_role('chronicler')) and status in ('draft','changes_requested','approved','scheduled')) with check (author_id = (select auth.uid()));

drop policy if exists revisions_read on public.submission_revisions;
create policy revisions_read on public.submission_revisions for select using (exists(select 1 from public.submissions s where s.id=submission_id and (s.author_id=(select auth.uid()) or (select private.has_role('editor')) or (select private.has_role('admin')))));
drop policy if exists revisions_insert on public.submission_revisions;
create policy revisions_insert on public.submission_revisions for insert with check (created_by=(select auth.uid()) and exists(select 1 from public.submissions s where s.id=submission_id and s.author_id=(select auth.uid()) and (select private.has_role('chronicler'))));

drop policy if exists reviews_read on public.agent_reviews;
create policy reviews_read on public.agent_reviews for select using (exists(select 1 from public.submissions s where s.id=submission_id and (s.author_id=(select auth.uid()) or (select private.has_role('editor')) or (select private.has_role('admin')))));

drop policy if exists media_read on public.media;
create policy media_read on public.media for select using (owner_id=(select auth.uid()) or (select private.has_role('editor')) or (select private.has_role('admin')));
drop policy if exists media_insert on public.media;
create policy media_insert on public.media for insert with check (owner_id=(select auth.uid()) and (select private.has_role('chronicler')));

drop policy if exists publish_requests_read on public.publish_requests;
create policy publish_requests_read on public.publish_requests for select using (requested_by=(select auth.uid()) or (select private.has_role('editor')) or (select private.has_role('admin')));

drop policy if exists subscriptions_self_read on public.subscriptions;
create policy subscriptions_self_read on public.subscriptions for select using (user_id=(select auth.uid()) or (select private.has_role('admin')));

drop policy if exists audit_admin_read on public.audit_log;
create policy audit_admin_read on public.audit_log for select using ((select private.has_role('admin')));

commit;
