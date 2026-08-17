from dataclasses import dataclass

from app.schemas.rights import RightType


@dataclass(frozen=True)
class TemplateContext:
    full_name: str
    institution_name: str
    contact_email: str | None = None
    account_reference: str | None = None


def render_request(right_type: RightType, ctx: TemplateContext) -> tuple[str, str, list[str]]:
    action = {
        RightType.ACCESS: "access to my personal data",
        RightType.RECTIFICATION: "rectification of inaccurate personal data",
        RightType.ERASURE: "erasure of personal data where legally applicable",
        RightType.RESTRICTION: "restriction of processing",
        RightType.OBJECTION: "objection to specified processing",
        RightType.MARKETING_SUPPRESSION: "cessation of direct marketing",
        RightType.CONSENT_WITHDRAWAL: "withdrawal of consent where consent is relied upon",
        RightType.CRB_DISPUTE: "review and correction of disputed credit information",
    }[right_type]

    subject = f"Personal data request: {action}"
    account_line = (
        f"Reference/account: {ctx.account_reference}\n" if ctx.account_reference else ""
    )
    body = (
        f"To {ctx.institution_name},\n\n"
        f"I am {ctx.full_name}. I am requesting {action}.\n"
        f"{account_line}"
        "Please confirm receipt, identify any information reasonably required to verify my identity, "
        "and respond through the applicable Kenyan legal and regulatory process.\n\n"
        "This request is intentionally limited to my own personal data and does not ask you to delete "
        "records that you are legally required to retain.\n"
    )

    warnings: list[str] = []
    if right_type == RightType.ERASURE:
        warnings.append(
            "Erasure is not absolute; preview the request against retention and sector obligations."
        )
    if right_type == RightType.CRB_DISPUTE:
        warnings.append(
            "Use subject-specific CRB evidence where available; do not infer reporting from public lists."
        )
    return subject, body, warnings
