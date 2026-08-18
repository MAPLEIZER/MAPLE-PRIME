package ke.co.kenyadatarights

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ScanPolicyTest {
    @Test
    fun scanIsForegroundBoundedAndNonPersistent() {
        assertTrue(ScanPolicy.requiresForeground)
        assertFalse(ScanPolicy.persistRawContent)
        assertTrue(ScanPolicy.maxSmsRows in 1..500)
        assertTrue(ScanPolicy.maxCallRows in 1..500)
        assertTrue(ScanPolicy.lookbackDays in 1..120)
    }

    @Test
    fun backgroundTransitionRequiresEphemeralResultsToBeCleared() {
        assertTrue(ScanPolicy.clearResultsOnBackground)
    }
}
