from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/legal", tags=["legal"])


class LegalSection(BaseModel):
    heading: str
    content: str


class LegalDocument(BaseModel):
    id: str
    title: str
    version: str
    last_updated: str
    jurisdiction: str
    summary: str
    sections: List[LegalSection]


PRIVACY_POLICY = LegalDocument(
    id="privacy-policy",
    title="EDWISE Institutional Learning Analytics — Privacy Policy",
    version="4.2",
    last_updated="2026-11-22",
    jurisdiction="CBSE, FERPA & Digital Personal Data Protection (DPDP)",
    summary=(
        "This Privacy Policy outlines how the EDWISE Learning Analytics Suite collects, processes, "
        "protects, and governs student academic records, attendance logs, and faculty evaluations "
        "under strict institutional confidentiality and regulatory compliance."
    ),
    sections=[
        LegalSection(
            heading="1. Regulatory Compliance (CBSE & FERPA)",
            content=(
                "EDWISE operates in strict alignment with the Family Educational Rights and Privacy Act "
                "(FERPA, 20 U.S.C. § 1232g), Central Board of Secondary Education (CBSE) data governance guidelines, "
                "and digital student protection standards. All Personally Identifiable Information (PII) is encrypted "
                "at rest with AES-256 and transmitted exclusively over TLS 1.3 encrypted tunnels."
            ),
        ),
        LegalSection(
            heading="2. Anti-Enumeration & Zero Account Discovery (Spec R-003)",
            content=(
                "To defend against automated scraping, identity enumeration, and credential brute-forcing, "
                "the student self-registration roster claim endpoint returns a uniform HTTP 202 Accepted response. "
                "The system never exposes whether a given admission number exists in the student roster to an unauthenticated client. "
                "Actual activation tokens are dispatched out-of-band to registered parental or student contacts."
            ),
        ),
        LegalSection(
            heading="3. Broken Object Level Authorization (BOLA) & Role Scoping",
            content=(
                "Access to student data is rigorously restricted by verified academic scope. Instructors may only access "
                "class sections and subjects officially assigned to them for the active academic session. Students can only "
                "inspect their own marks, attendance statistics, and personalized feedback. Anti-stigma presentation protocols "
                "ensure diagnostic alerts are private and constructive."
            ),
        ),
        LegalSection(
            heading="4. Assistive Machine Learning & Transparency Disclaimers",
            content=(
                "All machine learning predictions (including projected marks, risk indicators, and what-if simulations) "
                "are assistive demonstration indicators computed from historical attendance and evaluation patterns. "
                "In compliance with Transparency Rule R-015, machine learning inferences are never treated as definitive verdicts, "
                "causes, or automated academic punishments, and require explicit teacher intervention."
            ),
        ),
        LegalSection(
            heading="5. Cryptographic Audit Trail (Regulation R-014)",
            content=(
                "Any alteration to evaluated exam scores, attendance records, or student roster assignments is permanently "
                "stamped into an immutable audit ledger. Each log entry records the modifier user ID, precise UTC timestamp, "
                "before/after value deltas, and mandatory faculty justification reasons."
            ),
        ),
        LegalSection(
            heading="6. Data Minimization & Commercial Prohibition",
            content=(
                "EDWISE is an educational technology suite deployed exclusively for institutional management. Student data, "
                "behavioral logs, and academic metrics are never sold, monetized, profiled for commercial gain, or shared "
                "with third-party advertisers."
            ),
        ),
        LegalSection(
            heading="7. Student & Guardian Inquiries",
            content=(
                "Enrolled students and legal guardians have the right to inspect official records, verify recorded attendance, "
                "and request rectification of clerical discrepancies through their designated school administrative office."
            ),
        ),
    ],
)

TERMS_OF_SERVICE = LegalDocument(
    id="terms-of-service",
    title="EDWISE Institutional Learning Analytics — Terms of Service & Acceptable Use",
    version="4.2",
    last_updated="2026-11-22",
    jurisdiction="Institutional Academic Governance & Code of Conduct",
    summary=(
        "These Terms of Service govern authorized access, academic integrity requirements, "
        "and acceptable usage standards for faculty, administrative staff, and enrolled students."
    ),
    sections=[
        LegalSection(
            heading="1. Authorized Educational Access",
            content=(
                "Access to the EDWISE platform is granted exclusively to verified institutional personnel with legitimate educational "
                "interests. Unauthorized access attempts, automated scraping, or credential sharing is strictly prohibited."
            ),
        ),
        LegalSection(
            heading="2. Academic Integrity & Honest Evaluation",
            content=(
                "Faculty members and evaluators agree to record marks and attendance accurately and in good faith. Falsification "
                "of student records, intentional misgrading, or unauthorized score manipulation will result in institutional disciplinary "
                "proceedings and immediate audit escalation."
            ),
        ),
        LegalSection(
            heading="3. Account Security & Credential Safeguards",
            content=(
                "Users must maintain the confidentiality of their credentials and immediately notify the system administrator "
                "if they suspect unauthorized account activity. Sessions automatically timeout after periods of inactivity."
            ),
        ),
        LegalSection(
            heading="4. Faculty Sovereign Discretion Over ML Inferences",
            content=(
                "Instructors retain primary pedagogical discretion over all academic evaluations. Machine learning risk scores "
                "and AI-assisted lesson recommendations are advisory reference tools intended to assist early intervention."
            ),
        ),
        LegalSection(
            heading="5. Mandatory Audit Justifications (R-014)",
            content=(
                "Any retroactive update to a student mark or finalized attendance sheet requires a valid, clear explanation "
                "logged to the institutional audit ledger for administrative oversight."
            ),
        ),
        LegalSection(
            heading="6. Acceptable Platform Use",
            content=(
                "Users may not probe, scan, or test the vulnerability of the system or network, nor breach security or authentication "
                "measures. The doubt resolution hub and class notice board must remain professional and free from abusive language."
            ),
        ),
        LegalSection(
            heading="7. Termination & Account Suspension",
            content=(
                "The institution reserves the right to suspend or terminate portal access for any user found in breach of "
                "these terms or institutional codes of conduct."
            ),
        ),
    ],
)


@router.get("/privacy", response_model=LegalDocument)
def get_privacy_policy():
    """Retrieve the official EDWISE Institutional Privacy Policy (Publicly Accessible)."""
    return PRIVACY_POLICY


@router.get("/privacy-policy", response_model=LegalDocument)
def get_privacy_policy_alias():
    """Alias for privacy policy."""
    return PRIVACY_POLICY


@router.get("/terms", response_model=LegalDocument)
def get_terms_of_service():
    """Retrieve the official EDWISE Institutional Terms of Service (Publicly Accessible)."""
    return TERMS_OF_SERVICE


@router.get("/terms-of-service", response_model=LegalDocument)
def get_terms_of_service_alias():
    """Alias for terms of service."""
    return TERMS_OF_SERVICE


@router.get("/{doc_type}", response_model=LegalDocument)
def get_legal_document(doc_type: str):
    """Retrieve legal document by type ('privacy' or 'terms')."""
    clean = doc_type.lower().strip()
    if clean in ("privacy", "privacy-policy", "privacy_policy"):
        return PRIVACY_POLICY
    elif clean in ("terms", "terms-of-service", "terms_of_service", "tos"):
        return TERMS_OF_SERVICE
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Legal document '{doc_type}' not found. Supported: 'privacy', 'terms'.",
    )
