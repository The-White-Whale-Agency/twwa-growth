// Vercel Function (Fixture): nimmt das Kontaktformular entgegen und meldet die Anfrage per E-Mail.
// Env: MAIL_API_KEY, CONTACT_TO. Ohne Schlüssel antwortet die Funktion mit 503.

const clean = (v, max) => String(v ?? '').replace(/[\r\n]+/g, ' ').trim().slice(0, max);
const SOURCES = ['google-suche', 'google-maps', 'empfehlung', 'fahrzeug-baustelle', 'ki-assistent', 'sonstiges'];

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res.status(405).json({ error: 'method' });
  }
  const b = req.body || {};
  if (clean(b.website, 200)) return res.status(200).json({ ok: true }); // Honeypot

  const name = clean(b.name, 120);
  const kontakt = clean(b.kontakt, 200);
  const thema = clean(b.thema, 60);
  const quelle = SOURCES.includes(b.quelle) ? b.quelle : 'keine-angabe';
  const nachricht = String(b.nachricht ?? '').trim().slice(0, 4000);
  const consent = b.datenschutz === 'on' || b.datenschutz === true;
  if (name.length < 2 || kontakt.length < 3 || nachricht.length < 10 || !consent) {
    return res.status(400).json({ error: 'invalid' });
  }
  if (!process.env.MAIL_API_KEY) return res.status(503).json({ error: 'not_configured' });
  // Versand an den Betrieb; Betreff trägt die Quelle für die Anfragen-Zählung: [Quelle: google-maps]
  return res.status(200).json({ ok: true, subject: `Anfrage: ${thema} [Quelle: ${quelle}]` });
}
