package ke.co.kenyadatarights

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class SharedObservationTest {
    @Test
    fun sharedTextExtractsPhoneButDoesNotRetainRawMessage() {
        val input = "Your loan is due. Call +254 700 123 456 or use ExampleLoan. Ref 99821"
        val result = minimizeSharedObservation(input)

        assertTrue(result.phoneNumbers.contains("+254700123456"))
        assertFalse(result.toString().contains("Your loan is due"))
        assertEquals(0, result.rawTextLength)
    }

    @Test
    fun blankShareProducesEmptyObservation() {
        val result = minimizeSharedObservation("   ")
        assertTrue(result.phoneNumbers.isEmpty())
        assertTrue(result.tokens.isEmpty())
        assertEquals(0, result.rawTextLength)
    }
}
