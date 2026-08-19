package ke.co.kenyadatarights

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class MessageClassifierTest {
    @Test
    fun repaymentMessageProducesVersionedDerivedFeaturesAndClassification() {
        val raw = "Your KES 4,250 loan repayment is due tomorrow. Pay now to avoid late fees."
        val features = extractMessageFeatures(raw, sender = "20400")
        val result = classifyMessageFeatures(features)

        assertEquals("kdr-msg-v1", features.schemaVersion)
        assertEquals(64, features.hashedBuckets.size)
        assertTrue(features.repaymentHits > 0)
        assertEquals(LoanMessageLabel.LOAN_REPAYMENT_REMINDER, result.label)
        assertFalse(result.toString().contains(raw))
    }

    @Test
    fun ordinaryMessageDefaultsToNonLoan() {
        val result = classifyMessage("Team lunch moved to 1pm", sender = "Alice")
        assertEquals(LoanMessageLabel.NON_LOAN, result.label)
    }
}
