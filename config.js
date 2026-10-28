/* CruiseNight settings. The only file to edit when setting up.

   While SUPABASE_URL still holds the placeholder, the app runs in DEMO MODE:
   sample events, and submissions/approvals saved only in this browser.
   Paste your project's URL and anon public key (Supabase > Project Settings > API)
   to go live. The anon key is meant to be public; the database rules in
   schema.sql are what protect the data. */
window.CRUISE_CONFIG = {
  APP_NAME: 'CruiseNight',
  TAGLINE: 'Local car cruises, shows & meetups',

  // Colour theme: 'chrome', 'steel', 'neon' or 'violet' (compare them on themes.html).
  THEME: 'chrome',

  SUPABASE_URL: 'https://pgdwtprmbpguedxliioi.supabase.co',
  SUPABASE_ANON_KEY: 'sb_publishable_Cx9CuX8wXtkavognLYKPUA_zp0YRKlM',

  // Where the map opens before the user shares their location: [lat, lng].
  // Address lookups also prefer results within about 70 miles of it.
  DEFAULT_CENTER: [38.6270, -90.1994],   // St. Louis, MO
  DEFAULT_ZOOM: 10,

  // 'mi' or 'km'
  UNITS: 'mi',

  // Optional: limit address lookups to these countries, e.g. 'us' or 'us,ca'.
  GEOCODE_COUNTRIES: 'us',

  // How far ahead the list shows recurring dates.
  DAYS_AHEAD: 60
};
