package ke.co.kenyadatarights

data class SharedObservation(
    val phoneNumbers: Set<String>,
    val tokens: Set<String>,
    val rawTextLength: Int = 0,
)

private val phonePattern = Regex("(?:\\+?254|0)\\s*7(?:[\\s-]*\\d){8}")
private val tokenPattern = Regex("\\b[A-Za-z][A-Za-z0-9_-]{2,30}\\b")
private val stopWords = setOf(
    "the", "and", "your", "you", "loan", "call", "use", "ref", "due", "for", "from", "with", "this", "that",
)

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
        .filter { it.lowercase() !in stopWords }
        .filterNot { token -> token.any(Char::isDigit) && token.all { it.isDigit() } }
        .take(20)
        .toSet()

    // Raw text is intentionally discarded here. Only minimized identifiers survive.
    return SharedObservation(phoneNumbers = phones, tokens = tokens, rawTextLength = 0)
}
