package ke.co.kenyadatarights

import java.security.MessageDigest
import java.util.Locale
import kotlin.math.min

enum class LoanMessageLabel(val wireName: String) {
    NON_LOAN("non_loan"),
    LOAN_MARKETING("loan_marketing"),
    LOAN_APPLICATION("loan_application"),
    LOAN_APPROVAL("loan_approval"),
    LOAN_DISBURSEMENT("loan_disbursement"),
    LOAN_REPAYMENT_REMINDER("loan_repayment_reminder"),
    LOAN_OVERDUE_COLLECTION("loan_overdue_collection"),
    CRB_NOTICE("crb_notice"),
    LOAN_OTHER("loan_other"),
}

data class MessageFeatures(
    val schemaVersion: String = "kdr-msg-v1",
    val charLength: Int,
    val digitRatio: Double,
    val uppercaseRatio: Double,
    val loanTermHits: Int,
    val marketingHits: Int,
    val approvalHits: Int,
    val disbursementHits: Int,
    val repaymentHits: Int,
    val overdueHits: Int,
    val collectionHits: Int,
    val crbHits: Int,
    val amountHits: Int,
    val urlHits: Int,
    val phoneHits: Int,
    val senderIsShortcode: Boolean,
    val senderIsAlpha: Boolean,
    val hashedBuckets: List<Int>,
)

data class MessageClassification(
    val features: MessageFeatures,
    val label: LoanMessageLabel,
    val confidence: Double,
    val modelVersion: String = "rules-v1",
)

private val wordRegex = Regex("[A-Za-z0-9]{2,24}")
private val urlRegex = Regex("https?://|www\\.", RegexOption.IGNORE_CASE)
private val phoneRegex = Regex("(?:\\+?254|0)[1-9](?:[ -]?\\d){8}")
private val amountRegex = Regex("(?:KES|KSH\\.?|KSHS\\.?)\\s*[0-9][0-9,.]*", RegexOption.IGNORE_CASE)

private val loanTerms = setOf("loan", "loans", "credit", "borrow", "facility", "limit", "lender")
private val marketingTerms = setOf("apply", "offer", "eligible", "qualify", "instant", "available", "access")
private val approvalTerms = setOf("approved", "approval", "accepted", "successful")
private val disbursementTerms = setOf("disbursed", "disbursement", "credited", "sent")
private val repaymentTerms = setOf("repay", "repayment", "due", "pay", "installment", "instalment")
private val overdueTerms = setOf("overdue", "late", "arrears", "pastdue", "defaulted")
private val collectionTerms = setOf("collection", "collector", "recovery", "recover", "default", "legal")
private val crbTerms = setOf("crb", "bureau", "metropol", "transunion", "creditinfo")

private fun countHits(tokens: List<String>, vocabulary: Set<String>): Int =
    tokens.count { it in vocabulary }

private fun hashedBuckets(tokens: List<String>): List<Int> {
    val buckets = IntArray(64)
    tokens.take(256).forEach { token ->
        val digest = MessageDigest.getInstance("SHA-256").digest(token.toByteArray(Charsets.UTF_8))
        val bucket = (digest[0].toInt() and 0xff) and 63
        buckets[bucket] = min(3, buckets[bucket] + 1)
    }
    return buckets.toList()
}

fun extractMessageFeatures(raw: String, sender: String? = null): MessageFeatures {
    val normalized = raw.lowercase(Locale.ROOT)
    val tokens = wordRegex.findAll(normalized).map { it.value }.toList()
    val compactTokens = tokens.map { it.replace(" ", "") }
    val letters = raw.count(Char::isLetter)
    val digits = raw.count(Char::isDigit)
    val uppercase = raw.count { it.isLetter() && it.isUpperCase() }
    val denominator = raw.length.coerceAtLeast(1).toDouble()
    val senderValue = sender.orEmpty().trim()

    return MessageFeatures(
        charLength = raw.length.coerceAtMost(20_000),
        digitRatio = digits / denominator,
        uppercaseRatio = if (letters == 0) 0.0 else uppercase.toDouble() / letters,
        loanTermHits = countHits(compactTokens, loanTerms),
        marketingHits = countHits(compactTokens, marketingTerms),
        approvalHits = countHits(compactTokens, approvalTerms),
        disbursementHits = countHits(compactTokens, disbursementTerms),
        repaymentHits = countHits(compactTokens, repaymentTerms),
        overdueHits = countHits(compactTokens, overdueTerms),
        collectionHits = countHits(compactTokens, collectionTerms),
        crbHits = countHits(compactTokens, crbTerms),
        amountHits = amountRegex.findAll(raw).count(),
        urlHits = urlRegex.findAll(raw).count(),
        phoneHits = phoneRegex.findAll(raw).count(),
        senderIsShortcode = senderValue.length in 3..7 && senderValue.all(Char::isDigit),
        senderIsAlpha = senderValue.length >= 3 && senderValue.any(Char::isLetter) && senderValue.none(Char::isWhitespace),
        hashedBuckets = hashedBuckets(tokens),
    )
}

private fun confidence(base: Double, signal: Int): Double =
    min(0.98, base + min(signal, 8) * 0.04)

fun classifyMessageFeatures(features: MessageFeatures): MessageClassification {
    val loanSignal = features.loanTermHits + features.amountHits
    val result = when {
        features.collectionHits > 0 || (features.overdueHits >= 2 && loanSignal > 0) ->
            LoanMessageLabel.LOAN_OVERDUE_COLLECTION to confidence(0.62, features.collectionHits + features.overdueHits + loanSignal)
        features.crbHits > 0 && (loanSignal > 0 || features.overdueHits > 0) ->
            LoanMessageLabel.CRB_NOTICE to confidence(0.62, features.crbHits + loanSignal)
        features.repaymentHits > 0 && loanSignal > 0 ->
            LoanMessageLabel.LOAN_REPAYMENT_REMINDER to confidence(0.58, features.repaymentHits + loanSignal)
        features.disbursementHits > 0 && loanSignal > 0 ->
            LoanMessageLabel.LOAN_DISBURSEMENT to confidence(0.58, features.disbursementHits + loanSignal)
        features.approvalHits > 0 && loanSignal > 0 ->
            LoanMessageLabel.LOAN_APPROVAL to confidence(0.56, features.approvalHits + loanSignal)
        features.marketingHits > 0 && features.loanTermHits > 0 ->
            LoanMessageLabel.LOAN_MARKETING to confidence(0.54, features.marketingHits + features.loanTermHits)
        features.loanTermHits >= 2 -> LoanMessageLabel.LOAN_OTHER to confidence(0.50, features.loanTermHits)
        else -> LoanMessageLabel.NON_LOAN to 0.72
    }
    return MessageClassification(features = features, label = result.first, confidence = result.second)
}

fun classifyMessage(raw: String, sender: String? = null): MessageClassification =
    classifyMessageFeatures(extractMessageFeatures(raw, sender))
