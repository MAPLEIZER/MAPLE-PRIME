package ke.co.kenyadatarights

import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.Lifecycle

class MainActivity : ComponentActivity() {
    private var observation by mutableStateOf(SharedObservation(emptySet(), emptySet()))
    private var scanStatus by mutableStateOf("No device scan has run.")
    private var scanning by mutableStateOf(false)

    private val permissionRequest = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions(),
    ) { grants ->
        val granted = CommunicationAccess.requiredPermissions.all { grants[it] == true }
        if (granted) {
            scanCommunications()
        } else {
            scanStatus = "SMS / Call Log access was not granted. Nothing was read."
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        consumeIntent(intent)
        setContent {
            KdrTheme {
                KdrHome(
                    observation = observation,
                    scanAvailable = CommunicationAccess.available,
                    scanning = scanning,
                    scanStatus = scanStatus,
                    onScan = ::requestForegroundScan,
                )
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        consumeIntent(intent)
    }

    override fun onStop() {
        // Ephemeral scan results are deliberately discarded as soon as KDR leaves the foreground.
        observation = SharedObservation(emptySet(), emptySet())
        scanStatus = "Ephemeral results cleared when KDR left the foreground."
        super.onStop()
    }

    private fun consumeIntent(intent: Intent?) {
        if (intent?.action == Intent.ACTION_SEND && intent.type == "text/plain") {
            observation = minimizeSharedObservation(intent.getStringExtra(Intent.EXTRA_TEXT).orEmpty())
            scanStatus = "Shared text minimized in memory; raw content discarded."
        }
    }

    private fun requestForegroundScan() {
        if (!CommunicationAccess.available) {
            scanStatus = "This build is permission-free. Use Android Share → Kenya Data Rights instead."
            return
        }
        if (!lifecycle.currentState.isAtLeast(Lifecycle.State.RESUMED)) {
            scanStatus = "Scan blocked because KDR is not in the foreground."
            return
        }

        val missing = CommunicationAccess.requiredPermissions.filter {
            checkSelfPermission(it) != PackageManager.PERMISSION_GRANTED
        }
        if (missing.isNotEmpty()) {
            permissionRequest.launch(missing.toTypedArray())
        } else {
            scanCommunications()
        }
    }

    private fun scanCommunications() {
        if (!lifecycle.currentState.isAtLeast(Lifecycle.State.RESUMED) || scanning) return
        scanning = true
        scanStatus = "Scanning recent SMS and call identifiers locally…"

        Thread {
            val result = runCatching { CommunicationAccess.scan(this) }
            runOnUiThread {
                if (lifecycle.currentState.isAtLeast(Lifecycle.State.RESUMED)) {
                    result.onSuccess {
                        observation = it
                        scanStatus = "Scan complete. Raw SMS/call content was not stored."
                    }.onFailure {
                        observation = SharedObservation(emptySet(), emptySet())
                        scanStatus = "Scan failed; no communication data was retained."
                    }
                }
                scanning = false
            }
        }.start()
    }
}

private val KdrNavy = Color(0xFF0B1220)
private val KdrPanel = Color(0xFF111C2F)
private val KdrCyan = Color(0xFF67E8F9)
private val KdrGreen = Color(0xFF86EFAC)
private val KdrText = Color(0xFFE5EEF8)
private val KdrMuted = Color(0xFF94A3B8)

@androidx.compose.runtime.Composable
private fun KdrTheme(content: @androidx.compose.runtime.Composable () -> Unit) {
    MaterialTheme(
        colorScheme = darkColorScheme(
            primary = KdrCyan,
            secondary = KdrGreen,
            background = KdrNavy,
            surface = KdrPanel,
            onBackground = KdrText,
            onSurface = KdrText,
        ),
        content = content,
    )
}

@androidx.compose.runtime.Composable
private fun KdrHome(
    observation: SharedObservation,
    scanAvailable: Boolean,
    scanning: Boolean,
    scanStatus: String,
    onScan: () -> Unit,
) {
    Surface(modifier = Modifier.fillMaxSize()) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .background(KdrNavy)
                .verticalScroll(rememberScrollState())
                .padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            Text("Kenya Data Rights", color = KdrCyan, fontWeight = FontWeight.Bold, fontSize = 27.sp)
            Text(
                "Identify which regulated provider may be behind an app, number or message while keeping raw communications local and ephemeral.",
                color = KdrMuted,
                fontSize = 16.sp,
            )

            PrivacyCard(scanAvailable)

            if (scanAvailable) {
                Card(colors = CardDefaults.cardColors(containerColor = KdrPanel), shape = RoundedCornerShape(18.dp)) {
                    Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        Text("Foreground device scan", fontWeight = FontWeight.Bold, fontSize = 20.sp)
                        Text(
                            "Reads up to ${ScanPolicy.maxSmsRows} recent SMS rows and ${ScanPolicy.maxCallRows} recent call-log rows from the last ${ScanPolicy.lookbackDays} days only after you tap Scan.",
                            color = KdrMuted,
                        )
                        Button(onClick = onScan, enabled = !scanning) {
                            Text(if (scanning) "Scanning…" else "Scan recent SMS & calls")
                        }
                        Text(scanStatus, color = if (scanning) KdrCyan else KdrMuted, fontSize = 13.sp)
                    }
                }
            }

            if (observation.phoneNumbers.isEmpty() && observation.tokens.isEmpty()) {
                SharePrompt()
            } else {
                ObservationCard(observation)
            }

            RoadmapCard(scanAvailable)
        }
    }
}

@androidx.compose.runtime.Composable
private fun PrivacyCard(scanAvailable: Boolean) {
    Card(colors = CardDefaults.cardColors(containerColor = KdrPanel), shape = RoundedCornerShape(18.dp)) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("Local-first intake", color = KdrGreen, fontWeight = FontWeight.Bold)
            if (scanAvailable) {
                Text("Direct build: SMS and Call Log are read only after an explicit foreground scan.", color = KdrText)
                Text("No receiver/service runs in the background. Raw rows are immediately minimized and results clear on backgrounding.", color = KdrMuted)
            } else {
                Text("Play-compatible build: no SMS or Call Log permission is declared.", color = KdrText)
                Text("Use Android's Share action to provide one message or identifier explicitly.", color = KdrMuted)
            }
        }
    }
}

@androidx.compose.runtime.Composable
private fun SharePrompt() {
    Card(colors = CardDefaults.cardColors(containerColor = KdrPanel), shape = RoundedCornerShape(18.dp)) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text("Share something into KDR", fontWeight = FontWeight.Bold, fontSize = 20.sp)
            Text(
                "From Messages, a browser, notes or another app, choose Share → Kenya Data Rights. KDR extracts only candidate identifiers locally.",
                color = KdrMuted,
            )
        }
    }
}

@androidx.compose.runtime.Composable
private fun ObservationCard(observation: SharedObservation) {
    Card(colors = CardDefaults.cardColors(containerColor = KdrPanel), shape = RoundedCornerShape(18.dp)) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text("Ephemeral identifiers", fontWeight = FontWeight.Bold, fontSize = 20.sp)
            Text("Raw content retained: no", color = KdrGreen)

            if (observation.phoneNumbers.isNotEmpty()) {
                Text("Phone identifiers", color = KdrMuted)
                FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    observation.phoneNumbers.forEach { Chip(it) }
                }
            }

            if (observation.tokens.isNotEmpty()) {
                Text("Candidate labels", color = KdrMuted)
                FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    observation.tokens.take(20).forEach { Chip(it) }
                }
            }

            Spacer(Modifier.height(2.dp))
            Button(onClick = { /* Upload remains intentionally disabled until explicit consent/review is complete. */ }) {
                Text("Review mapping before sharing")
            }
            Text("Community upload remains disabled in this Android alpha shell.", color = KdrMuted, fontSize = 13.sp)
        }
    }
}

@androidx.compose.runtime.Composable
private fun Chip(value: String) {
    Box(
        modifier = Modifier
            .background(Color(0xFF17263E), RoundedCornerShape(999.dp))
            .padding(horizontal = 11.dp, vertical = 7.dp),
        contentAlignment = Alignment.Center,
    ) {
        Text(value, color = KdrText, fontSize = 13.sp)
    }
}

@androidx.compose.runtime.Composable
private fun RoadmapCard(scanAvailable: Boolean) {
    Card(colors = CardDefaults.cardColors(containerColor = KdrPanel), shape = RoundedCornerShape(18.dp)) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("Android alpha boundary", fontWeight = FontWeight.Bold)
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("minSdk 23", color = KdrCyan)
                Spacer(Modifier.width(12.dp))
                Text("targetSdk 36", color = KdrMuted)
            }
            Text(
                if (scanAvailable) "Direct/sideload flavor · foreground-only communication scan" else "Play flavor · permission-free share workflow",
                color = KdrMuted,
            )
        }
    }
}
