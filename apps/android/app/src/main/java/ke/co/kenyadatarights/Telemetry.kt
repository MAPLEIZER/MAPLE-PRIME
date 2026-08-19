package ke.co.kenyadatarights

import java.net.URI

private fun jsonEscape(value: String): String = buildString {
    value.forEach { ch ->
        when (ch) {
            '\\' -> append("\\\\")
            '"' -> append("\\\"")
            '\n' -> append("\\n")
            '\r' -> append("\\r")
            '\t' -> append("\\t")
            else -> if (ch.code < 0x20) append("\\u%04x".format(ch.code)) else append(ch)
        }
    }
}

private fun quoted(value: String): String = "\"${jsonEscape(value)}\""

private fun MessageFeatures.toJsonString(): String = buildString {
    append("{")
    append("\"schema_version\":${quoted(schemaVersion)},")
    append("\"char_length\":$charLength,")
    append("\"digit_ratio\":$digitRatio,")
    append("\"uppercase_ratio\":$uppercaseRatio,")
    append("\"loan_term_hits\":$loanTermHits,")
    append("\"marketing_hits\":$marketingHits,")
    append("\"approval_hits\":$approvalHits,")
    append("\"disbursement_hits\":$disbursementHits,")
    append("\"repayment_hits\":$repaymentHits,")
    append("\"overdue_hits\":$overdueHits,")
    append("\"collection_hits\":$collectionHits,")
    append("\"crb_hits\":$crbHits,")
    append("\"amount_hits\":$amountHits,")
    append("\"url_hits\":$urlHits,")
    append("\"phone_hits\":$phoneHits,")
    append("\"sender_is_shortcode\":$senderIsShortcode,")
    append("\"sender_is_alpha\":$senderIsAlpha,")
    append("\"hashed_buckets\":[${hashedBuckets.joinToString(",")}]")
    append("}")
}

data class TelemetryEvent(
    val eventId: String,
    val clientId: String,
    val sourceKind: String,
    val appVersion: String,
    val modelVersion: String,
    val predictedLabel: String,
    val confidence: Double,
    val userLabel: String?,
    val features: MessageFeatures,
) {
    fun toJson(): String = buildString {
        append("{")
        append("\"event_id\":${quoted(eventId)},")
        append("\"client_id\":${quoted(clientId)},")
        append("\"source_kind\":${quoted(sourceKind)},")
        append("\"app_version\":${quoted(appVersion)},")
        append("\"model_version\":${quoted(modelVersion)},")
        append("\"predicted_label\":${quoted(predictedLabel)},")
        append("\"confidence\":$confidence,")
        if (userLabel == null) append("\"user_label\":null,") else append("\"user_label\":${quoted(userLabel)},")
        append("\"features\":${features.toJsonString()}")
        append("}")
    }

    companion object {
        fun fromClassification(
            clientId: String,
            sourceKind: String,
            appVersion: String,
            classification: MessageClassification,
            eventId: String = java.util.UUID.randomUUID().toString(),
            userLabel: LoanMessageLabel? = null,
        ): TelemetryEvent = TelemetryEvent(
            eventId = eventId,
            clientId = clientId,
            sourceKind = sourceKind,
            appVersion = appVersion,
            modelVersion = classification.modelVersion,
            predictedLabel = classification.label.wireName,
            confidence = classification.confidence,
            userLabel = userLabel?.wireName,
            features = classification.features,
        )
    }
}

fun telemetryBatchJson(events: List<TelemetryEvent>): String =
    "{\"events\":[${events.joinToString(",") { it.toJson() }}]}"

fun validateServerUrl(value: String): Boolean = runCatching {
    val uri = URI(value.trim())
    uri.scheme.equals("https", ignoreCase = true) &&
        !uri.host.isNullOrBlank() &&
        uri.userInfo == null && uri.query == null && uri.fragment == null &&
        (uri.path.isNullOrBlank() || uri.path == "/")
}.getOrDefault(false)
