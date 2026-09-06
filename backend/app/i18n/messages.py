from typing import Dict


MESSAGES: Dict[str, Dict[str, str]] = {
    "report_received": {
        "roman_urdu": "Aapki report mil gayi. Hum check kar rahe hain.",
        "en": "Your report has been received. We are reviewing it.",
        "urdu_script": "آپ کی رپورٹ مل گئی ہے۔ ہم چیک کر رہے ہیں۔",
    },
    "ai_verified": {
        "roman_urdu": "AI ne aapki report check kar li hai.",
        "en": "AI has verified your report.",
        "urdu_script": "AI نے آپ کی رپورٹ چیک کر لی ہے۔",
    },
    "dispatched": {
        "roman_urdu": "Team bhej di gai hai. Wo aa rahe hain.",
        "en": "A rescue team has been dispatched. They are on their way.",
        "urdu_script": "ٹیم بھیج دی گئی ہے۔ وہ آ رہے ہیں۔",
    },
    "team_en_route": {
        "roman_urdu": "Team raaste mein hai. Taqreeban {eta} minute mein pohanchein ge.",
        "en": "Team is en route. Estimated arrival in {eta} minutes.",
        "urdu_script": "ٹیم راستے میں ہے۔ تقریباً {eta} منٹ میں پہنچیں گے۔",
    },
    "resolved": {
        "roman_urdu": "Madad mil gai. Shukriya ke aap ne report ki.",
        "en": "Help has been received. Thank you for reporting.",
        "urdu_script": "مدد مل گئی۔ شکریہ کہ آپ نے رپورٹ کی۔",
    },
    "queued_offline": {
        "roman_urdu": "Internet nahi hai. Report save ho gai hai — signal aane par bhej dein ge.",
        "en": "No internet. Report saved — will send when signal returns.",
        "urdu_script": "انٹرنیٹ نہیں ہے۔ رپورٹ محفوظ ہو گئی ہے — سگنل آنے پر بھیج دیں گے۔",
    },
    "rejected": {
        "roman_urdu": "Report reject ho gai hai.",
        "en": "Report has been rejected.",
        "urdu_script": "رپورٹ مسترد کر دی گئی ہے۔",
    },
    "sms_received": {
        "roman_urdu": "Aapki SMS report mil gai. Code: {code}. Status: reliefpulse.pk/status/{code}",
        "en": "Your SMS report received. Code: {code}. Track: reliefpulse.pk/status/{code}",
        "urdu_script": "آپ کی ایس ایم ایس رپورٹ مل گئی۔ کوڈ: {code}",
    },
}


def get_message(key: str, lang: str = "roman_urdu", **kwargs: str) -> str:
    """
    Get a localized message by key and language.

    Args:
        key: Message key (e.g., 'report_received')
        lang: Language code ('roman_urdu', 'en', 'urdu_script')
        **kwargs: Format variables (e.g., eta='45', code='RP-2847')

    Returns:
        Formatted message string, falling back to English if key/lang missing.
    """
    msg_dict = MESSAGES.get(key, {})
    template = msg_dict.get(lang) or msg_dict.get("en", key)
    if kwargs:
        try:
            return template.format(**kwargs)
        except KeyError:
            return template
    return template

