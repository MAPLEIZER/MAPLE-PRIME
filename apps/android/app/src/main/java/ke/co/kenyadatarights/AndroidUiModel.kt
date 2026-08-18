package ke.co.kenyadatarights

enum class KdrSection(val label: String, val shortLabel: String) {
    HOME("Home", "Home"),
    SCAN("Scan", "Scan"),
    LEARN("Learn", "Learn"),
    SERVER("Server", "Server"),
    RIGHTS("Rights", "Rights"),
}

fun defaultKdrSection(): KdrSection = KdrSection.HOME

data class OfflineRightCard(
    val title: String,
    val summary: String,
    val nextStep: String,
)

fun offlineRightsCards(): List<OfflineRightCard> = listOf(
    OfflineRightCard(
        title = "Access your personal data",
        summary = "Ask an organisation what personal data it holds about you, why it is processed, and how it is used or shared.",
        nextStep = "Use KDR's rights-request tools on the desktop dashboard to prepare an access request.",
    ),
    OfflineRightCard(
        title = "Correct inaccurate data",
        summary = "Request correction when personal information is inaccurate, incomplete, misleading, or no longer current.",
        nextStep = "Keep evidence of the correct information and the date you requested the change.",
    ),
    OfflineRightCard(
        title = "Erase data where the law allows",
        summary = "Erasure is not absolute. KDR treats deletion as a rights request that may be limited by legal retention or other lawful processing duties.",
        nextStep = "State what data you want erased and why, then review any lawful-retention explanation you receive.",
    ),
    OfflineRightCard(
        title = "Object to or restrict processing",
        summary = "You may be able to object to particular uses of your data or ask for processing to be restricted while a dispute is reviewed.",
        nextStep = "Identify the specific processing activity rather than asking an organisation to stop all processing indiscriminately.",
    ),
)
