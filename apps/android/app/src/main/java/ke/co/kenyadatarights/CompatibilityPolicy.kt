package ke.co.kenyadatarights

data class AndroidCapabilities(
    val runtimePermissions: Boolean,
    val localClassification: Boolean,
    val httpsTelemetry: Boolean,
    val notificationChannels: Boolean,
    val adaptiveIcons: Boolean,
    val biometricPrompt: Boolean,
)

fun capabilitiesForApi(api: Int): AndroidCapabilities = AndroidCapabilities(
    runtimePermissions = api >= 23,
    localClassification = api >= 23,
    httpsTelemetry = api >= 23,
    notificationChannels = api >= 26,
    adaptiveIcons = api >= 26,
    biometricPrompt = api >= 28,
)
