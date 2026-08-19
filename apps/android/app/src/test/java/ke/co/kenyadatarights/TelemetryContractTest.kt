package ke.co.kenyadatarights

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class TelemetryContractTest {
    @Test
    fun telemetryPayloadContainsDerivedFeaturesButNeverRawMessage() {
        val raw = "Your loan of KES 5000 is overdue. Pay today."
        val classified = classifyMessage(raw, sender = "LOANAPP")
        val event = TelemetryEvent.fromClassification(
            clientId = "2f77f39d-7e42-47e1-bf15-dedfd74e7e04",
            sourceKind = "shared_text",
            appVersion = "0.1.0-alpha.1",
            classification = classified,
        )
        val json = event.toJson().toString()

        assertTrue(json.contains("kdr-msg-v1"))
        assertTrue(json.contains("hashed_buckets"))
        assertFalse(json.contains(raw))
        assertFalse(json.contains("raw_text"))
        assertFalse(json.contains("message_body"))
    }

    @Test
    fun serverUrlValidatorRequiresHttps() {
        assertTrue(validateServerUrl("https://kdr.example.ts.net"))
        assertFalse(validateServerUrl("http://192.168.1.10:8080"))
        assertFalse(validateServerUrl("https://example.com/path"))
    }
}
