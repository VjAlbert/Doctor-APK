// Generic behavioural heuristics. These flag *combinations* of capabilities
// seen together in malware; legitimate apps can occasionally match too.

rule sms_exfiltration
{
    meta:
        key = "sms_exfiltration"
        severity = "high"
    strings:
        $inbox = "content://sms/inbox"
        $sms = "android.provider.Telephony.SMS_RECEIVED"
        $send1 = "api.telegram.org/bot"
        $send2 = "discord.com/api/webhooks"
        $send3 = "sendTextMessage"
    condition:
        ($inbox or $sms) and 1 of ($send*)
}

rule ransom_note
{
    meta:
        key = "ransom_note"
        severity = "high"
    strings:
        $a = "your files have been encrypted" nocase
        $b = "pay the ransom" nocase
        $c = "decrypt your files" nocase
        $d = "bitcoin" nocase
    condition:
        2 of ($a, $b, $c) or (1 of ($a, $b, $c) and $d)
}

rule crypto_miner
{
    meta:
        key = "crypto_miner"
        severity = "high"
    strings:
        $a = "stratum+tcp://"
        $b = "stratum+ssl://"
        $c = "xmrig" nocase
        $d = "cryptonight" nocase
        $e = "coinhive" nocase
    condition:
        any of them
}

rule accessibility_overlay_banker
{
    meta:
        key = "accessibility_overlay_banker"
        severity = "high"
    strings:
        $acc1 = "performGlobalAction"
        $acc2 = "getRootInActiveWindow"
        $ovl1 = "TYPE_APPLICATION_OVERLAY"
        $ovl2 = "SYSTEM_ALERT_WINDOW"
        $ovl3 = "addView"
        $sms = "content://sms"
        $hide = "setComponentEnabledSetting"
    condition:
        1 of ($acc*) and 1 of ($ovl*) and ($sms or $hide)
}

rule icon_hiding
{
    meta:
        key = "icon_hiding"
        severity = "medium"
    strings:
        $a = "setComponentEnabledSetting"
        $b = "COMPONENT_ENABLED_STATE_DISABLED"
        $c = "android.intent.category.LAUNCHER"
    condition:
        $a and $b and $c
}
