"""
Starter templates per common Banneker portco type. Coworkers pick one, then
edit themes/queries to match their actual portco. Themes are a list of
{name, queries} dicts so order is preserved.
"""

TEMPLATES: dict[str, dict] = {
    "Blank": {
        "description": "Start from scratch.",
        "themes": [
            {"name": "", "queries": []},
        ],
    },
    "Cybersecurity portco": {
        "description": "OT/cyber, ICS, regulation, breaches. Built for Industrial Defender.",
        "themes": [
            {
                "name": "Breaches & incidents",
                "queries": [
                    "OT cyberattack", "ICS ransomware", "critical infrastructure breach",
                    "utility cyberattack", "water utility cyberattack", "power grid cyberattack",
                    "oil gas pipeline cyberattack", "manufacturing ransomware shutdown",
                    "energy sector breach", "SCADA attack",
                ],
            },
            {
                "name": "Competitive / market (M&A, raises)",
                "queries": [
                    "Claroty OT security", "Dragos OT cybersecurity", "Nozomi Networks",
                    "Armis OT", "TXOne Networks",
                    "OT cybersecurity acquisition", "OT cybersecurity acquires",
                    "ICS cybersecurity acquisition", "OT security funding round",
                    "OT cybersecurity Series funding",
                ],
            },
            {
                "name": "EU regulation (NIS2 / CRA / DORA)",
                "queries": [
                    "NIS2 directive", "Cyber Resilience Act", "DORA cybersecurity",
                    "ENISA OT", "NIS2 enforcement fine",
                ],
            },
            {
                "name": "North American regulation (NERC-CIP / TSA / CISA)",
                "queries": [
                    "NERC CIP", "NERC CIP audit penalty", "FERC cybersecurity",
                    "TSA pipeline cybersecurity directive", "CISA OT advisory",
                    "CISA critical infrastructure", "EPA water cybersecurity",
                ],
            },
            {
                "name": "OT / ICS cybersecurity",
                "queries": [
                    "OT cybersecurity", "ICS cybersecurity", "operational technology security",
                    "SCADA security", "industrial control system security",
                ],
            },
        ],
    },
    "Healthcare portco": {
        "description": "FDA, payer activity, M&A, clinical events.",
        "themes": [
            {
                "name": "FDA & regulation",
                "queries": [
                    "FDA approval", "FDA clearance", "FDA warning letter",
                    "FDA 510k", "FDA breakthrough device", "CMS rule", "CMS reimbursement",
                ],
            },
            {
                "name": "Payer & reimbursement",
                "queries": [
                    "payer coverage decision", "Medicare reimbursement", "Medicaid coverage",
                    "private payer coverage", "prior authorization", "value-based care",
                ],
            },
            {
                "name": "Competitive / market (M&A, raises)",
                "queries": [
                    "healthcare acquisition", "medtech acquisition", "digital health acquisition",
                    "healthcare Series funding", "medtech IPO", "biotech M&A",
                ],
            },
            {
                "name": "Clinical & trial events",
                "queries": [
                    "clinical trial results", "Phase 3 results", "Phase 2 results",
                    "trial readout", "primary endpoint met", "FDA advisory committee",
                ],
            },
        ],
    },
    "Fintech portco": {
        "description": "Payments, regulation, networks, competitive moves.",
        "themes": [
            {
                "name": "Payments & networks",
                "queries": [
                    "Visa Mastercard fees", "interchange fees", "real-time payments",
                    "FedNow", "Zelle", "ACH rule change", "Stripe Adyen",
                ],
            },
            {
                "name": "Regulation (CFPB / OCC / FDIC)",
                "queries": [
                    "CFPB rule", "OCC enforcement", "FDIC fintech", "BSA AML enforcement",
                    "fintech regulation", "open banking rule",
                ],
            },
            {
                "name": "Competitive / market (M&A, raises)",
                "queries": [
                    "fintech acquisition", "payments acquisition", "fintech Series funding",
                    "fintech IPO", "neobank funding", "payments M&A",
                ],
            },
            {
                "name": "Breaches & fraud",
                "queries": [
                    "fintech data breach", "payment fraud", "card skimming",
                    "ATO account takeover", "fintech security incident",
                ],
            },
        ],
    },
    "Vertical SaaS portco": {
        "description": "Vertical news, competitive, M&A, customer wins.",
        "themes": [
            {
                "name": "Vertical-specific news",
                "queries": [
                    # User edits this to their vertical
                    "vertical news placeholder",
                ],
            },
            {
                "name": "Competitive / market (M&A, raises)",
                "queries": [
                    "vertical SaaS acquisition", "vertical SaaS Series funding",
                    "vertical software M&A", "industry software acquired",
                ],
            },
            {
                "name": "Customer wins & losses",
                "queries": [
                    "company selects software", "customer wins software", "software deployment",
                    "switches from", "replaces software with",
                ],
            },
            {
                "name": "Pricing & packaging moves",
                "queries": [
                    "SaaS pricing change", "pricing model SaaS", "AI pricing software",
                    "usage-based pricing software",
                ],
            },
        ],
    },
    "Industrials portco": {
        "description": "Supply chain, OEMs, regulation, commodities.",
        "themes": [
            {
                "name": "Supply chain & logistics",
                "queries": [
                    "supply chain disruption", "shipping rates", "container rates",
                    "port congestion", "trucking rates", "freight market",
                ],
            },
            {
                "name": "OEM & manufacturer activity",
                "queries": [
                    "OEM announcement", "manufacturer plant", "factory expansion",
                    "manufacturing capacity", "production cut",
                ],
            },
            {
                "name": "Regulation & tariffs",
                "queries": [
                    "tariff industrials", "trade policy manufacturing", "EPA industrial",
                    "OSHA enforcement", "Inflation Reduction Act manufacturing",
                ],
            },
            {
                "name": "Competitive / market (M&A, raises)",
                "queries": [
                    "industrial acquisition", "manufacturing M&A", "industrial Series funding",
                    "industrial IPO",
                ],
            },
        ],
    },
    "Climate / energy portco": {
        "description": "Policy, subsidies, capital, regional dynamics.",
        "themes": [
            {
                "name": "Policy & subsidies",
                "queries": [
                    "Inflation Reduction Act", "IRA tax credit", "DOE loan", "EU green deal",
                    "California climate disclosure", "SEC climate rule",
                ],
            },
            {
                "name": "Capital raises & deals",
                "queries": [
                    "climate tech funding", "climate tech Series", "energy storage funding",
                    "EV funding", "battery acquisition", "climate IPO",
                ],
            },
            {
                "name": "Competitive / market",
                "queries": [
                    "solar panel pricing", "battery storage pricing", "EV charging deployment",
                    "heat pump adoption", "hydrogen project",
                ],
            },
            {
                "name": "Customer wins & deployments",
                "queries": [
                    "utility selects", "corporate PPA signed", "off-take agreement",
                    "data center renewables",
                ],
            },
        ],
    },
}


def get_template_names() -> list[str]:
    """Return template names with Blank last so users see real ones first."""
    names = [n for n in TEMPLATES.keys() if n != "Blank"]
    return names + ["Blank"]


def get_template(name: str) -> dict:
    return TEMPLATES.get(name, TEMPLATES["Blank"])
