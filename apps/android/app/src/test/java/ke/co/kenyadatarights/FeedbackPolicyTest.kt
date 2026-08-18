package ke.co.kenyadatarights

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class FeedbackPolicyTest {
    @Test
    fun explicitSingleSharedMessageMayCarryHumanLabel() {
        assertEquals(
            LoanMessageLabel.LOAN_MARKETING,
            verifiedUserLabel(
                sourceKind = "shared_text",
                classificationCount = 1,
                selected = LoanMessageLabel.LOAN_MARKETING,
            ),
        )
    }

    @Test
    fun bulkScanNeverAppliesOneHumanLabelAcrossMultipleMessages() {
        assertNull(
            verifiedUserLabel(
                sourceKind = "sms_scan",
                classificationCount = 20,
                selected = LoanMessageLabel.NON_LOAN,
            ),
        )
        assertNull(
            verifiedUserLabel(
                sourceKind = "shared_text",
                classificationCount = 2,
                selected = LoanMessageLabel.NON_LOAN,
            ),
        )
    }
}
