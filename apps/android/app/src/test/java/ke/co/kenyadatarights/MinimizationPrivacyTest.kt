package ke.co.kenyadatarights

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class MinimizationPrivacyTest {
    @Test
    fun ordinarySentenceWordsAndNamesDoNotSurviveMinimization() {
        val result = minimizeSharedObservation(
            "Hello Austin, your loan is due tomorrow from ZENKA. Open ExampleLoan to pay.",
        )

        assertFalse(result.tokens.contains("Hello"))
        assertFalse(result.tokens.contains("Austin"))
        assertFalse(result.tokens.contains("tomorrow"))
        assertTrue(result.tokens.contains("ZENKA"))
        assertTrue(result.tokens.contains("ExampleLoan"))
    }

    @Test
    fun commonKenyanMobilePrefixesNormalizeWithoutKeepingRawFormatting() {
        val result = minimizeSharedObservation("0700 123 456 and 0112-345-678")
        assertTrue(result.phoneNumbers.contains("+254700123456"))
        assertTrue(result.phoneNumbers.contains("+254112345678"))
        assertFalse(result.toString().contains("0700 123 456"))
    }
}
