from __future__ import annotations

"""Template library for motion drafting."""

from neuro_san.interfaces.coded_tool import CodedTool

try:  # optional imports for runtime
    from apps.legal_discovery.models import (
        Fact,
        LegalTheory,
        NarrativeDiscrepancy,
        Document,
    )
except Exception:  # pragma: no cover - used when app context missing
    Fact = LegalTheory = NarrativeDiscrepancy = Document = None  # type: ignore


class TemplateLibrary(CodedTool):
    """Load motion templates and populate them with case data."""

    MOTION_TEMPLATES = {
        "motion_to_dismiss": (
            "Draft a Motion to Dismiss using the following facts:\n{facts}\n"
            "Accepted theories:\n{theories}\nOpposition:\n{conflicts}"
        ),
        "motion_for_summary_judgment": (
            "Prepare a Motion for Summary Judgment grounded on these facts:\n{facts}\n"
            "Accepted theories:\n{theories}\nOpposition:\n{conflicts}"
        ),
        "motion_in_limine": (
            "Draft a Motion in Limine considering these facts:\n{facts}\n"
            "Accepted theories:\n{theories}\nOpposition:\n{conflicts}"
        ),
        "motion_to_compel": (
            "Draft a Motion to Compel discovery using these facts:\n{facts}\n"
            "Accepted theories:\n{theories}\nOpposition:\n{conflicts}"
        ),
        "motion_for_protective_order": (
            "Prepare a Motion for Protective Order grounded on these facts:\n{facts}\n"
            "Accepted theories:\n{theories}\nOpposition:\n{conflicts}"
        ),
        "declaration_in_support_of_rfo_move_away": (
            "Draft a responsive Declaration in Support of/Response to an RFO (Move-Away) using these facts:\n{facts}\n"
            "Accepted theories:\n{theories}\nOpposition/risks:\n{conflicts}\n"
            "Ensure compliance with local rules and include child best-interest arguments as applicable."
        ),
        "motion_to_set_aside_or_vacate_judgment": (
            "Prepare a Motion to Set Aside/Vacate Judgment based on these facts:\n{facts}\n"
            "Accepted theories:\n{theories}\nOpposition:\n{conflicts}\n"
            "Cite statutory grounds, timelines, and standards; include notice language."
        ),
        "trial_brief": (
            "Draft a Trial Brief summarizing issues, facts, and law:\n{facts}\n"
            "Accepted theories:\n{theories}\nOpposition:\n{conflicts}"
        ),
        "motion_for_sanctions": (
            "Draft a Motion for Sanctions using these facts:\n{facts}\n"
            "Accepted theories:\n{theories}\nOpposition:\n{conflicts}"
        ),
        "motion_for_injunction": (
            "Draft a Motion for Injunction (temporary or permanent) considering:\n{facts}\n"
            "Accepted theories:\n{theories}\nOpposition:\n{conflicts}"
        ),
        "motion_to_seal": (
            "Prepare a Motion to Seal with privacy and public access considerations using:\n{facts}\n"
            "Accepted theories:\n{theories}\nOpposition:\n{conflicts}"
        ),
        "motion_to_reopen_discovery": (
            "Draft a Motion to Reopen Discovery using:\n{facts}\n"
            "Accepted theories:\n{theories}\nOpposition:\n{conflicts}\n"
            "Justify good cause and lack of prejudice."
        ),
        "motion_to_shorten_time": (
            "Draft a Request/Notice to Shorten Time for Hearing based on:\n{facts}\n"
            "Accepted theories:\n{theories}\nOpposition:\n{conflicts}\n"
            "Include urgency, prejudice, and supporting declarations."
        ),
    }

    def available(self) -> list[str]:
        """Return available motion types."""
        return list(self.MOTION_TEMPLATES.keys())

    def build_prompt(self, motion_type: str) -> str:
        """Build an LLM prompt for the given motion type."""
        template = self.MOTION_TEMPLATES.get(motion_type)
        if not template:
            raise ValueError("Unknown motion type")

        facts_text = "No facts available."
        theories_text = "No accepted theories."
        opposition_text = "No opposition recorded."
        evidence_text = "No scored documents."
        try:
            if Fact is not None:
                facts = Fact.query.order_by(Fact.id).all()
                if facts:
                    facts_text = "\n".join(f"- {f.text}" for f in facts)
            if LegalTheory is not None:
                theories = LegalTheory.query.filter_by(status="accepted").all()
                if theories:
                    theories_text = "\n".join(
                        f"- {t.theory_name}: {t.description or ''}" for t in theories
                    )
            if NarrativeDiscrepancy is not None:
                opp = NarrativeDiscrepancy.query.order_by(
                    NarrativeDiscrepancy.id
                ).all()
                if opp:
                    opposition_text = "\n".join(
                        f"- {d.conflicting_claim} vs {d.evidence_excerpt}"
                        for d in opp
                    )
            if Document is not None:
                docs = (
                    Document.query.order_by(Document.probative_value.desc())
                    .limit(3)
                    .all()
                )
                if docs:
                    evidence_text = "\n".join(
                        f"- {d.name}: p={d.probative_value:.2f}, a={d.admissibility_risk:.2f}, n={d.narrative_alignment:.2f}"
                        for d in docs
                    )
        except Exception:  # pragma: no cover - missing DB/app context
            pass

        return template.format(
            facts=facts_text, theories=theories_text, conflicts=opposition_text
        ) + f"\nTop Evidence:\n{evidence_text}"
