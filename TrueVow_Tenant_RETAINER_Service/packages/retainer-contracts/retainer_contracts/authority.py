from __future__ import annotations

from enum import StrEnum


class AuthorityClass(StrEnum):
    SYS_ADMIN = "SYS_ADMIN"
    FIRM_POLICY = "FIRM_POLICY"
    STAFF_AUTH = "STAFF_AUTH"
    ATTY_AUTH = "ATTY_AUTH"
    CLIENT_AUTH = "CLIENT_AUTH"
    PROHIBITED = "PROHIBITED"


class AuthorityAction(StrEnum):
    CANDIDATE_IMPORT = "retainer.candidate.import"
    REPRESENTATION_PREPARE = "retainer.representation.prepare"
    REPRESENTATION_DECIDE = "retainer.representation.decide"
    CONFLICT_SEARCH = "retainer.conflict.search"
    CONFLICT_CLEAR_OR_HOLD = "retainer.conflict.clear_or_hold"
    TEMPLATE_RESOLVE = "retainer.template.resolve"
    PACKAGE_GENERATE = "retainer.package.generate"
    PACKAGE_AUTHORIZE_DELIVERY = "retainer.package.authorize_delivery"
    PACKAGE_DELIVER = "retainer.package.deliver"
    ESIGN_CONSENT = "retainer.esign.consent"
    SIGNATURE_CLIENT_APPLY = "retainer.signature.client_apply"
    SIGNATURE_FIRM_APPLY = "retainer.signature.firm_apply"
    QUESTION_LEGAL_RESPOND = "retainer.question.legal_respond"
    REMINDER_SEND = "retainer.reminder.send"
    ACTIVATION_AUTHORIZE = "retainer.activation.authorize"
    ACTIVATION_EXECUTE = "retainer.activation.execute"
    PLATFORM_SELF_AUTHORIZE = "retainer.platform.self_authorize"


ACTION_AUTHORITY: dict[AuthorityAction, AuthorityClass] = {
    AuthorityAction.CANDIDATE_IMPORT: AuthorityClass.SYS_ADMIN,
    AuthorityAction.REPRESENTATION_PREPARE: AuthorityClass.STAFF_AUTH,
    AuthorityAction.REPRESENTATION_DECIDE: AuthorityClass.ATTY_AUTH,
    AuthorityAction.CONFLICT_SEARCH: AuthorityClass.FIRM_POLICY,
    AuthorityAction.CONFLICT_CLEAR_OR_HOLD: AuthorityClass.ATTY_AUTH,
    AuthorityAction.TEMPLATE_RESOLVE: AuthorityClass.FIRM_POLICY,
    AuthorityAction.PACKAGE_GENERATE: AuthorityClass.FIRM_POLICY,
    AuthorityAction.PACKAGE_AUTHORIZE_DELIVERY: AuthorityClass.FIRM_POLICY,
    AuthorityAction.PACKAGE_DELIVER: AuthorityClass.SYS_ADMIN,
    AuthorityAction.ESIGN_CONSENT: AuthorityClass.CLIENT_AUTH,
    AuthorityAction.SIGNATURE_CLIENT_APPLY: AuthorityClass.CLIENT_AUTH,
    AuthorityAction.SIGNATURE_FIRM_APPLY: AuthorityClass.ATTY_AUTH,
    AuthorityAction.QUESTION_LEGAL_RESPOND: AuthorityClass.ATTY_AUTH,
    AuthorityAction.REMINDER_SEND: AuthorityClass.FIRM_POLICY,
    AuthorityAction.ACTIVATION_AUTHORIZE: AuthorityClass.ATTY_AUTH,
    AuthorityAction.ACTIVATION_EXECUTE: AuthorityClass.FIRM_POLICY,
    AuthorityAction.PLATFORM_SELF_AUTHORIZE: AuthorityClass.PROHIBITED,
}
