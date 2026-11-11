"""Generate tamper-evident Carbon Passport HTML Verification Reports (English & Telugu) & JSON Audit Bundles."""

import html
import json
from typing import Any, Dict


REPORT_LABELS = {
    "en": {
        "title": "CarbonKheti · Digital Carbon Passport",
        "subtitle": "INNOVASIA 2K26 · PS-13 · Tamper-Evident Smallholder Agroforestry MRV Dossier",
        "print_btn": "Print / Save as PDF",
        "disclosure": (
            "<strong>Scientific &amp; Regulatory Disclosure:</strong> This prototype dossier uses clearly labeled "
            "demonstration/proxy satellite observations and a synthetic reference calibration model ({model}). "
            "It is an auditable MRV evidence package and <strong>not</strong> an official registry carbon-credit "
            "certificate (Verra/CCTS VVB audit required for issuance). Target automated MRV cost of ≤₹100/ha/yr is a design target."
        ),
        "s1": "1. Farm & Landholder Digital Identity",
        "farmer": "Farmer",
        "parcel": "Farm Parcel",
        "area": "Gross / Core Area",
        "centroid": "Centroid (WGS84)",
        "s2": "2. Conservative Biomass & Carbon Accounting (IPCC 2006 Chain)",
        "agb": "AGB Point / 95% CI",
        "net_bio": "Conservative Net Biomass",
        "carbon": "Carbon Stock (×0.47)",
        "co2e": "Issuable CO₂e (Lower Bound)",
        "s3": "3. Carbon Fraud Radar & Integrity Findings",
        "s4": "4. Farmer Field Evidence Manifest",
        "s5": "5. SHA-256 Hash-Chain Audit Trail",
        "no_alerts": "No fraud flags triggered. Automated checks passed.",
        "no_ev": "No photo evidence uploaded yet.",
        "verified_intact": "VERIFIED INTACT",
        "failed": "FAILED",
    },
    "te": {
        "title": "CarbonKheti · డిజిటల్ కార్బన్ పాస్‌పోర్ట్",
        "subtitle": "INNOVASIA 2K26 · PS-13 · చిన్న రైతుల అగ్రోఫారెస్ట్రీ MRV ధృవీకరణ నివేదిక",
        "print_btn": "ప్రింట్ చేయండి / PDF గా సేవ్ చేయండి",
        "disclosure": (
            "<strong>శాస్త్రీయ &amp; నియంత్రణ గమనిక:</strong> ఈ నివేదిక ప్రదర్శన కోసం రూపొందించిన "
            "ఉపగ్రహ డేటా మరియు సింథటిక్ మోడల్ ({model}) ఆధారంగా తయారు చేయబడింది. ఇది ఆడిట్ చేయదగిన MRV ఆధారాల పత్రం మాత్రమే — "
            "అధికారిక కార్బన్ క్రెడిట్ సర్టిఫికెట్ <strong>కాదు</strong> (జారీ చేయడానికి VVB ఆడిట్ అవసరం). "
            "హెక్టారుకు సంవత్సరానికి ≤₹100 ఖర్చు అనేది ప్రాజెక్ట్ లక్ష్యం."
        ),
        "s1": "1. రైతు & పొలం డిజిటల్ గుర్తింపు వివరాలు",
        "farmer": "రైతు పేరు",
        "parcel": "పొలం పేరు",
        "area": "మొత్తం / 10మీ కోర్ విస్తీర్ణం",
        "centroid": "పొలం కేంద్రం (GPS)",
        "s2": "2. నమ్మదగిన జీవద్రవ్యం & కార్బన్ లెక్కలు (IPCC 2006)",
        "agb": "చెట్ల జీవద్రవ్యం / 95% CI",
        "net_bio": "నికర కనిష్ట జీవద్రవ్యం",
        "carbon": "కార్బన్ నిల్వ (×0.47)",
        "co2e": "జారీ చేయదగిన CO₂e (కనిష్ట అంచనా)",
        "s3": "3. కార్బన్ ఫ్రాడ్ రాడార్ తనిఖీ ఫలితాలు",
        "s4": "4. రైతు పంపిన పొలం ఫోటో ఆధారాలు",
        "s5": "5. SHA-256 హ్యాష్-చైన్ ఆడిట్ రికార్డు గొలుసు",
        "no_alerts": "ఎలాంటి మోసం లేదా అనుమానాస్పద హెచ్చరికలు లేవు.",
        "no_ev": "ఇంకా ఫోటో ఆధారాలు అప్‌లోడ్ కాలేదు.",
        "verified_intact": "సురక్షితం (VERIFIED)",
        "failed": "విఫలమైంది (BROKEN)",
    },
}


def render_carbon_passport_html(dossier: Dict[str, Any], lang: str = "en") -> str:
    """
    Render a clean, self-contained, print-ready Carbon Passport Verification Dossier
    in English ('en') or Telugu ('te').
    """
    lbl = REPORT_LABELS.get(lang, REPORT_LABELS["en"])
    passport = dossier["passport"]
    farm = dossier["farm"]
    farmer = dossier["farmer"]
    estimate = dossier["latest_estimate"]
    sat = dossier["latest_observation"]
    risk = dossier["risk_summary"]
    alerts = dossier["fraud_alerts"]
    evidence = dossier["evidence_records"]
    chain = dossier["chain_verification"]

    esc = html.escape
    status_color = "#059669" if chain["verified"] and risk["risk_score"] < 45 else "#b45309"
    if not chain["verified"] or risk["risk_score"] >= 75:
        status_color = "#dc2626"

    alert_rows = "".join(
        f"""
        <tr>
          <td><span class="badge badge-{esc(a['severity'].lower())}">{esc(a['severity'])}</span></td>
          <td class="mono">{esc(a['alert_type'])}</td>
          <td>{a['risk_score']}/100</td>
          <td>{esc(a['explanation'])}</td>
        </tr>
        """
        for a in alerts
    ) or f'<tr><td colspan="4" style="text-align:center;color:#4b5563;">{lbl["no_alerts"]}</td></tr>'

    ev_rows = "".join(
        f"""
        <tr>
          <td class="mono">{esc(e['id'])}</td>
          <td>{esc(e['original_filename'])}</td>
          <td class="mono">{esc(e['file_sha256'][:16])}…</td>
          <td class="mono">{esc(e['perceptual_dhash'])}</td>
          <td>{'Yes' if e['exif_present'] else 'Stripped'}</td>
          <td>{esc(e['upload_timestamp'][:19])}</td>
        </tr>
        """
        for e in evidence
    ) or f'<tr><td colspan="6" style="text-align:center;color:#4b5563;">{lbl["no_ev"]}</td></tr>'

    chain_rows = "".join(
        f"""
        <tr>
          <td class="mono">#{b['index']}</td>
          <td class="mono">{esc(b['event_type'])}</td>
          <td class="mono">{esc(b['timestamp'][:19])}</td>
          <td class="mono">{esc(b['prev_hash'][:14])}…</td>
          <td class="mono">{esc(b['stored_hash'][:14])}…</td>
          <td>{'✅ VALID' if b['valid'] else '❌ BROKEN'}</td>
        </tr>
        """
        for b in chain["blocks"]
    )

    assump = json.loads(estimate["assumptions_json"]) if estimate and isinstance(estimate.get("assumptions_json"), str) else (estimate.get("assumptions", {}) if estimate else {})
    disclosure_html = lbl["disclosure"].format(model=esc(passport["model_version"]))

    return f"""<!DOCTYPE html>
<html lang="{esc(lang)}">
<head>
<meta charset="UTF-8" />
<title>{esc(lbl['title'])} — {esc(passport['passport_id'])}</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Telugu:wght@400;600;700;800&display=swap" rel="stylesheet" />
<style>
  body {{ font-family: 'Segoe UI', 'Noto Sans Telugu', system-ui, sans-serif; background: #FAF8F4; color: #111827; margin: 0; padding: 32px; line-height: 1.5; }}
  .sheet {{ max-width: 960px; margin: 0 auto; background: #FFFFFF; border: 1px solid #E5E0D5; border-radius: 14px; padding: 36px; box-shadow: 0 10px 30px rgba(13,40,24,0.06); }}
  .header {{ display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid #0D2818; padding-bottom: 18px; margin-bottom: 22px; }}
  .brand {{ font-size: 24px; font-weight: 800; color: #0D2818; letter-spacing: -0.02em; }}
  .sub {{ font-size: 12px; color: #4B5563; margin-top: 2px; }}
  .pill {{ display: inline-block; padding: 6px 14px; border-radius: 999px; font-weight: 700; font-size: 12px; color: #fff; background: {status_color}; }}
  .banner {{ background: #FEF3C7; border: 1px solid #F59E0B; color: #92400E; padding: 10px 14px; border-radius: 8px; font-size: 12px; margin-bottom: 20px; }}
  h2 {{ font-size: 15px; text-transform: uppercase; letter-spacing: 0.04em; color: #163A24; border-bottom: 1px solid #E5E7EB; padding-bottom: 6px; margin-top: 26px; }}
  .grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 14px 0; }}
  .card {{ background: #FAF8F4; border: 1px solid #E5E0D5; border-radius: 10px; padding: 12px 14px; }}
  .card .lbl {{ font-size: 11px; color: #6B7280; }}
  .card .val {{ font-size: 20px; font-weight: 800; color: #0D2818; margin-top: 2px; }}
  .card .hint {{ font-size: 11px; color: #4B5563; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 10px; }}
  th, td {{ border: 1px solid #E5E7EB; padding: 8px 10px; text-align: left; vertical-align: top; }}
  th {{ background: #F3EFE6; color: #0D2818; font-weight: 700; }}
  .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 11px; }}
  .badge {{ padding: 2px 8px; border-radius: 999px; font-size: 10px; font-weight: 700; }}
  .badge-critical {{ background: #FEE2E2; color: #991B1B; }}
  .badge-high {{ background: #FFEDD5; color: #9A3412; }}
  .badge-medium {{ background: #FEF3C7; color: #92400E; }}
  .badge-low {{ background: #D1FAE5; color: #065F46; }}
  .actions {{ margin-bottom: 16px; text-align: right; }}
  .btn {{ background: #0D2818; color: #fff; border: none; padding: 9px 16px; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 13px; }}
  @media print {{ .actions {{ display: none; }} body {{ background: #fff; padding: 0; }} .sheet {{ box-shadow: none; border: none; }} }}
</style>
</head>
<body>
<div class="actions">
  <button class="btn" onclick="window.print()">{esc(lbl['print_btn'])}</button>
</div>
<div class="sheet">
  <div class="header">
    <div>
      <div class="brand">{esc(lbl['title'])}</div>
      <div class="sub">{esc(lbl['subtitle'])}</div>
      <div class="mono" style="margin-top:6px;">Passport ID: <strong>{esc(passport['passport_id'])}</strong> · Issued: {esc(passport['issued_at'][:19])} UTC</div>
    </div>
    <div style="text-align:right;">
      <span class="pill">{esc(passport['verification_status'])}</span>
      <div class="mono" style="margin-top:8px;">Head SHA-256:<br>{esc(passport['head_hash'][:32])}…</div>
    </div>
  </div>

  <div class="banner">{disclosure_html}</div>

  <h2>{esc(lbl['s1'])}</h2>
  <div class="grid">
    <div class="card"><div class="lbl">{esc(lbl['farmer'])}</div><div class="val" style="font-size:15px;">{esc(farmer['name'])}</div><div class="hint">{esc(farmer['village'])}, {esc(farmer['district'])}, {esc(farmer['state'])}</div></div>
    <div class="card"><div class="lbl">{esc(lbl['parcel'])}</div><div class="val" style="font-size:15px;">{esc(farm['name'])}</div><div class="hint">{esc(farm['agroforestry_type'])} · {esc(farm['species'])}</div></div>
    <div class="card"><div class="lbl">{esc(lbl['area'])}</div><div class="val">{farm['gross_area_ha']} ha</div><div class="hint">10m inner buffer: {farm['core_area_ha']} ha ({farm['core_pixels_10m']} px)</div></div>
    <div class="card"><div class="lbl">{esc(lbl['centroid'])}</div><div class="val mono" style="font-size:14px;">{farm['centroid_lat']}, {farm['centroid_lon']}</div><div class="hint">Doc: {esc(farmer.get('land_doc_ref') or 'N/A')}</div></div>
  </div>

  <h2>{esc(lbl['s2'])}</h2>
  {f'''
  <div class="grid">
    <div class="card"><div class="lbl">{esc(lbl['agb'])}</div><div class="val">{estimate['agb_point_t_ha']} t/ha</div><div class="hint">95% CI: [{estimate['agb_ci_lower_t_ha']} – {estimate['agb_ci_upper_t_ha']}] t/ha</div></div>
    <div class="card"><div class="lbl">{esc(lbl['net_bio'])}</div><div class="val">{estimate['net_additional_biomass_t']} t</div><div class="hint">AGB ({estimate['agb_lower_total_t']}t) + BGB ({estimate['bgb_lower_total_t']}t) − base − leak</div></div>
    <div class="card"><div class="lbl">{esc(lbl['carbon'])}</div><div class="val">{estimate['carbon_tC']} tC</div><div class="hint">IPCC 0.47 carbon fraction</div></div>
    <div class="card"><div class="lbl">{esc(lbl['co2e'])}</div><div class="val" style="color:#059669;">{estimate['co2e_conservatively_issuable_t']} tCO₂e</div><div class="hint">Gross {estimate['co2e_gross_t']} tCO₂e − {assump.get('permanence_buffer_pct', 15)}% buffer</div></div>
  </div>
  <table>
    <tr><th>Parameter</th><th>Value</th><th>Scientific Basis / Scope</th></tr>
    <tr><td>Sensor Mode &amp; Cloud Cover</td><td>{esc(estimate['sensor_mode'])}</td><td>Cloud: {sat['cloud_cover_pct'] if sat else 'N/A'}% · {esc(sat['is_simulated_label'] if sat else 'N/A')}</td></tr>
    <tr><td>Included Carbon Pools</td><td>AGB (Satellite ML) + BGB (Root-to-Shoot {assump.get('root_to_shoot_ratio', 0.24)})</td><td>Soil Organic Carbon (SOC), dead wood &amp; litter conservatively excluded</td></tr>
    <tr><td>Conversion Formula</td><td>Net Lower Biomass × 0.47 × (44/12) × (1 − Buffer)</td><td>Credits calculated strictly from 95% lower bound</td></tr>
  </table>
  ''' if estimate else '<p>No biomass estimation run yet.</p>'}

  <h2>{esc(lbl['s3'])}</h2>
  <p>Risk Score: <strong>{risk['risk_score']}/100 ({esc(risk['risk_level'])})</strong> · Active Alerts: {risk['active_alert_count']}</p>
  <table>
    <tr><th>Severity</th><th>Check Type</th><th>Risk</th><th>Explanation</th></tr>
    {alert_rows}
  </table>

  <h2>{esc(lbl['s4'])}</h2>
  <table>
    <tr><th>Evidence ID</th><th>Filename</th><th>File SHA-256</th><th>Perceptual dHash</th><th>EXIF</th><th>Uploaded (UTC)</th></tr>
    {ev_rows}
  </table>

  <h2>{esc(lbl['s5'])} ({chain['block_count']} Blocks · {esc(lbl['verified_intact'] if chain['verified'] else lbl['failed'])})</h2>
  <table>
    <tr><th>Block</th><th>Event</th><th>Timestamp (UTC)</th><th>Previous Hash</th><th>Record Hash</th><th>Status</th></tr>
    {chain_rows}
  </table>
</div>
</body>
</html>
"""
