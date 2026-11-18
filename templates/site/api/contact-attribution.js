// twwa-growth: attribution additions for an existing Vercel form handler (api/contact.js).
// Merge into the handler; do not replace it. No cookies, no personal data stored by TWWA.
// 1. Form: add <select name="quelle"> ("Wie haben Sie uns gefunden?": google_suche, google_maps, ki_assistent,
//    empfehlung, portal, social, werbung, sonstiges) and a hidden <input name="seite"> filled with location.pathname.
// 2. Handler additions:

const SOURCES = new Set(["google_suche", "google_maps", "ki_assistent", "empfehlung", "portal", "social", "werbung", "sonstiges"]);

export function twwaAttribution(body, headers) {
  // synthetic test from leads.py probe: answer 200 without sending mail
  if (body && (body._twwa_probe === "1" || headers["x-twwa-probe"] === "1")) return { probe: true };
  const quelle = SOURCES.has(body?.quelle) ? body.quelle : "unbekannt";
  const seite = typeof body?.seite === "string" && body.seite.startsWith("/") ? body.seite.slice(0, 120) : "unbekannt";
  return { probe: false, quelle, seite, subjectTag: `[Anfrage | ${quelle} | ${seite}]` };
}

// In the handler, before sending:
//   const a = twwaAttribution(req.body, req.headers);
//   if (a.probe) return res.status(200).json({ ok: true, probe: true });
//   subject = `${a.subjectTag} ${subject}`;   // the operator imports tagged notifications with leads.py
// Optional (Vercel Pro, vercel.custom_events = true):
//   import { track } from "@vercel/analytics/server";
//   await track("anfrage", { quelle: a.quelle, seite: a.seite });
