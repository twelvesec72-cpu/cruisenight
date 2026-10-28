# CruiseNight

Local car cruises, shows and meetups. The public submits events, the admin approves them,
and approved events get directions, contact links, socials, add-to-calendar and an "I'm going" count.

A static PWA (`index.html`, `sw.js`, `config.js`) on GitHub Pages, with Supabase for the data,
poster storage and the admin login.

## Demo mode
Until `config.js` has real Supabase keys, the app runs on sample data saved in the browser.
Any email and password signs in to `#/admin`. To reset the demo, clear site data.

## Going live
1. Create a free project at supabase.com.
2. Open **SQL Editor**, paste all of `schema.sql`, and run it.
3. **Authentication > Users > Add user**: create your admin login.
   **Authentication > Sign In / Providers**: turn off "Allow new users to sign up".
4. In the SQL Editor, using your email:
   ```sql
   insert into public.admins (user_id) select id from auth.users where email = 'you@example.com';
   ```
5. **Project Settings > API**: copy the Project URL and the `anon` `public` key into `config.js`.
   Set `DEFAULT_CENTER` to your town.
6. Run `python tests/rls_probe.py` (every line should PASS), then reject the probe event in `#/admin`.
7. Upload the folder to a GitHub Pages repo.

## Deploying an update
Bump `CACHE` in `sw.js` on every deploy, or installed phones keep the old version.
Never rename the `cn.` localStorage keys.

## Look and logo
- Colour theme: `THEME` in `config.js` (`chrome`, `steel`, `neon`, `violet`). Compare them side by side on `themes.html`.
- The logo is the Gateway Arch drawn from its real catenary curve (`tools/arch_geometry.py`).
  After changing the theme, regenerate the app icons to match:
  `python tools/make_icons.py tools/arch_pts.json . <theme>`
