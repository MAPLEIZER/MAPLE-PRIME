package ke.co.kenyadatarights

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class CompatibilityPolicyTest {
    @Test
    fun api23KeepsCoreScanClassificationAndHttpsAvailable() {
        val capabilities = capabilitiesForApi(23)
        assertTrue(capabilities.runtimePermissions)
        assertTrue(capabilities.localClassification)
        assertTrue(capabilities.httpsTelemetry)
        assertFalse(capabilities.notificationChannels)
        assertFalse(capabilities.adaptiveIcons)
        assertFalse(capabilities.biometricPrompt)
    }

    @Test
    fun newerApisProgressivelyEnableModernUxWithoutRaisingMinSdk() {
        assertTrue(capabilitiesForApi(26).notificationChannels)
        assertTrue(capabilitiesForApi(26).adaptiveIcons)
        assertTrue(capabilitiesForApi(28).biometricPrompt)
    }
}
