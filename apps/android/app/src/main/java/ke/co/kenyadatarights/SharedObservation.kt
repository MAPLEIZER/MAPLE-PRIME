package ke.co.kenyadatarights

data class SharedObservation(
    val phoneNumbers: Set<String>,
    val tokens: Set<String>,
    val rawTextLength: Int = 0,
)

private val phonePattern = Regex("(?:\\+?254|0)\\s*[1-9](?:[\\s-]*\\d){8}")
private val tokenPattern = Regex("\\b[A-Za-z][A-Za-z0-9_-]{2,30}\\b")

private fun isLikelyServiceIdentifier(token: String): Boolean {
    val letters = token.filter(Char::isLetter)
    if (letters.length < 3) return false
    val allUpper = letters.all(Char::isUpperCase)
    val internalUpper = token.drop(1).any(Char::isUpperCase)
    val structured = token.contains('-') || token.contains('_')
    val alphanumeric = token.any(Char::isDigit) && token.any(Char::isLetter)
    return allUpper || internalUpper || structured || alphanumeric
}

fun minimizeSharedObservation(raw: String): SharedObservation {
    if (raw.isBlank()) return SharedObservation(emptySet(), emptySet())

    val phones = phonePattern.findAll(raw)
        .map { match ->
            val compact = match.value.filter { it.isDigit() || it == '+' }
            when {
                compact.startsWith("0") -> "+254${compact.drop(1)}"
                compact.startsWith("254") -> "+$compact"
                else -> compact
            }
        }
        .toSet()

    val tokens = tokenPattern.findAll(raw)
        .map { it.value.trim() }
        .filter(::isLikelyServiceIdentifier)
        .take(20)
        .toSet()

    // The returned object never retains the supplied text or its original length.
    return SharedObservation(phoneNumbers = phones, tokens = tokens, rawTextLength = 0)
}
