package ke.co.kenyadatarights

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class AndroidUiContractTest {
    @Test
    fun primary_navigation_is_product_shaped_not_one_long_scroll() {
        assertEquals(
            listOf("Home", "Scan", "Learn", "Server", "Rights"),
            KdrSection.entries.map { it.label },
        )
        assertEquals(KdrSection.HOME, defaultKdrSection())
    }

    @Test
    fun offline_rights_cards_exist_for_core_data_rights() {
        val rights = offlineRightsCards()
        assertTrue(rights.size >= 4)
        assertTrue(rights.any { it.title.contains("Access") })
        assertTrue(rights.any { it.title.contains("Correct") })
        assertTrue(rights.any { it.title.contains("Erase") })
        assertTrue(rights.any { it.title.contains("Object") })
    }

    @Test
    fun mobile_status_endpoint_uses_the_authenticated_mobile_surface() {
        val config = ServerConfig("https://kdr.example.ts.net", "secret")
        assertEquals(
            "https://kdr.example.ts.net/api/v1/mobile/status",
            mobileStatusUrl(config),
        )
    }
}
