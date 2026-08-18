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
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
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
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.Lifecycle
import java.util.UUID

class MainActivity : ComponentActivity() {
    private var observation by mutableStateOf(SharedObservation(emptySet(), emptySet()))
    private var observationSource by mutableStateOf("manual")
    private var feedbackLabel by mutableStateOf<LoanMessageLabel?>(null)
    private var scanStatus by mutableStateOf("No device scan has run.")
    private var scanning by mutableStateOf(false)
    private var serverUrl by mutableStateOf("")
    private var pairingToken by mutableStateOf("")
    private var telemetryStatus by mutableStateOf("Telemetry is not paired.")
    private var uploading by mutableStateOf(false)

    @Volatile
    private var foregroundAccessAllowed = false

    private val permissionRequest = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions(),
    ) { grants ->
        val granted = CommunicationAccess.requiredPermissions.all { grants[it] == true }
        if (granted && foregroundAccessAllowed) {
            scanCommunications()
        } else if (!granted) {
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
                    serverUrl = serverUrl,
                    pairingToken = pairingToken,
                    telemetryStatus = telemetryStatus,
                    uploading = uploading,
                    feedbackLabel = feedbackLabel,
                    allowFeedback = observationSource == "shared_text" && observation.classifications.size == 1,
                    onFeedbackLabel = { feedbackLabel = it },
                    onServerUrlChange = { serverUrl = it.take(500) },
                    onPairingTokenChange = { pairingToken = it.take(200) },
                    onSavePairing = ::savePairing,
                    onClearPairing = ::clearPairing,
                    onUpload = ::sendDerivedTelemetry,
                    onScan = ::requestForegroundScan,
                )
            }
        }
    }

    override fun onResume() {
        super.onResume()
        foregroundAccessAllowed = true
        ServerConfigStore.load(this)?.let {
            serverUrl = it.serverUrl
            pairingToken = it.token
            telemetryStatus = "Paired to ${it.serverUrl}. Upload remains manual."
        }
    }

    override fun onPause() {
        foregroundAccessAllowed = false
        scanning = false
        uploading = false
        observation = SharedObservation(emptySet(), emptySet())
        observationSource = "manual"
        feedbackLabel = null
        pairingToken = ""
        scanStatus = "Ephemeral results cleared when KDR left the foreground."
        super.onPause()
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        consumeIntent(intent)
    }

    private fun consumeIntent(intent: Intent?) {
        if (intent?.action == Intent.ACTION_SEND && intent.type == "text/plain") {
            val raw = intent.getStringExtra(Intent.EXTRA_TEXT).orEmpty()
            val minimized = minimizeSharedObservation(raw)
            observation = minimized.copy(classifications = listOf(classifyMessage(raw)))
            observationSource = "shared_text"
            feedbackLabel = null
            scanStatus = "Shared text classified/minimized in memory; raw content discarded."
        }
    }

    private fun requestForegroundScan() {
        if (!CommunicationAccess.available) {
            scanStatus = "This build is permission-free. Use Android Share → Kenya Data Rights instead."
            return
        }
        if (!foregroundAccessAllowed || !lifecycle.currentState.isAtLeast(Lifecycle.State.RESUMED)) {
            scanStatus = "Scan blocked because KDR is not in the foreground."
            return
        }
        val missing = CommunicationAccess.requiredPermissions.filter {
            checkSelfPermission(it) != PackageManager.PERMISSION_GRANTED
        }
        if (missing.isNotEmpty()) permissionRequest.launch(missing.toTypedArray()) else scanCommunications()
    }

    private fun scanCommunications() {
        if (!foregroundAccessAllowed || !lifecycle.currentState.isAtLeast(Lifecycle.State.RESUMED) || scanning) return
        feedbackLabel = null
        scanning = true
        scanStatus = "Scanning and classifying recent SMS/call identifiers locally…"
        Thread {
            val result = runCatching { CommunicationAccess.scan(this) { foregroundAccessAllowed } }
            runOnUiThread {
                if (foregroundAccessAllowed && lifecycle.currentState.isAtLeast(Lifecycle.State.RESUMED)) {
                    result.onSuccess {
                        observation = it
                        observationSource = "sms_scan"
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

    private fun savePairing() {
        val config = ServerConfig(serverUrl.trim(), pairingToken.trim())
        if (!validateServerUrl(config.serverUrl)) {
            telemetryStatus = "Use the HTTPS server URL shown by the KDR installer."
            return
        }
        runCatching { ServerConfigStore.save(this, config) }
            .onSuccess { telemetryStatus = "Pairing saved using Android Keystore encryption. Upload remains manual." }
            .onFailure { telemetryStatus = "Pairing could not be saved." }
    }

    private fun clearPairing() {
        ServerConfigStore.clear(this)
        pairingToken = ""
        serverUrl = ""
        telemetryStatus = "Pairing cleared."
    }

    private fun stableClientId(): String {
        val prefs = getSharedPreferences("kdr_client", MODE_PRIVATE)
        val existing = prefs.getString("client_id", null)
        if (existing != null) return existing
        val created = UUID.randomUUID().toString()
        prefs.edit().putString("client_id", created).apply()
        return created
    }

    private fun sendDerivedTelemetry() {
        if (!foregroundAccessAllowed || uploading) return
        val config = ServerConfigStore.load(this)
        if (config == null) {
            telemetryStatus = "Pair the app with your HTTPS KDR server first."
            return
        }
        val classifications = observation.classifications.take(25)
        if (classifications.isEmpty()) {
            telemetryStatus = "Nothing to send. Scan or share a message first."
            return
        }
        val verifiedLabel = verifiedUserLabel(
            sourceKind = observationSource,
            classificationCount = classifications.size,
            selected = feedbackLabel,
        )
        uploading = true
        telemetryStatus = "Sending derived features only…"
        Thread {
            var accepted = 0
            var attempted = 0
            val clientId = stableClientId()
            for (classification in classifications) {
                if (!foregroundAccessAllowed) break
                attempted += 1
                val event = TelemetryEvent.fromClassification(
                    clientId = clientId,
                    sourceKind = observationSource,
                    appVersion = BuildConfig.VERSION_NAME,
                    classification = classification,
                    userLabel = verifiedLabel,
                )
                val code = runCatching { TelemetryClient.submit(config, event) }.getOrDefault(0)
                if (code in 200..299) accepted += 1
            }
            runOnUiThread {
                if (foregroundAccessAllowed) {
                    val feedbackNote = if (accepted > 0 && verifiedLabel != null) {
                        feedbackLabel = null
                        " Human label accepted for this single shared message."
                    } else {
                        ""
                    }
                    telemetryStatus = "$accepted of $attempted derived observations accepted. No raw message body was sent.$feedbackNote"
                }
                uploading = false
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
    serverUrl: String,
    pairingToken: String,
    telemetryStatus: String,
    uploading: Boolean,
    feedbackLabel: LoanMessageLabel?,
    allowFeedback: Boolean,
    onFeedbackLabel: (LoanMessageLabel?) -> Unit,
    onServerUrlChange: (String) -> Unit,
    onPairingTokenChange: (String) -> Unit,
    onSavePairing: () -> Unit,
    onClearPairing: () -> Unit,
    onUpload: () -> Unit,
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
                "Identify providers, classify loan-app communications locally, and optionally contribute privacy-minimized learning signals to your own KDR server.",
                color = KdrMuted,
                fontSize = 16.sp,
            )
            PrivacyCard(scanAvailable)
            if (scanAvailable) {
                Card(colors = CardDefaults.cardColors(containerColor = KdrPanel), shape = RoundedCornerShape(18.dp)) {
                    Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        Text("Foreground device scan", fontWeight = FontWeight.Bold, fontSize = 20.sp)
                        Text(
                            "Reads up to ${ScanPolicy.maxSmsRows} recent SMS rows and ${ScanPolicy.maxCallRows} call-log rows from the last ${ScanPolicy.lookbackDays} days after you tap Scan.",
                            color = KdrMuted,
                        )
                        Button(onClick = onScan, enabled = !scanning) {
                            Text(if (scanning) "Scanning…" else "Scan recent SMS & calls")
                        }
                        Text(scanStatus, color = if (scanning) KdrCyan else KdrMuted, fontSize = 13.sp)
                    }
                }
            }
            if (observation.phoneNumbers.isEmpty() && observation.tokens.isEmpty() && observation.classifications.isEmpty()) {
                SharePrompt()
            } else {
                ObservationCard(
                    observation = observation,
                    allowFeedback = allowFeedback,
                    feedbackLabel = feedbackLabel,
                    onFeedbackLabel = onFeedbackLabel,
                )
            }
            TelemetryCard(
                serverUrl,
                pairingToken,
                telemetryStatus,
                uploading,
                observation.classifications.isNotEmpty(),
                onServerUrlChange,
                onPairingTokenChange,
                onSavePairing,
                onClearPairing,
                onUpload,
            )
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
                Text("No receiver/service runs in the background. Raw rows are immediately minimized; results clear on backgrounding.", color = KdrMuted)
            } else {
                Text("Play-compatible build: no SMS or Call Log permission is declared.", color = KdrText)
                Text("Use Android Share to provide one message explicitly; classification still happens locally.", color = KdrMuted)
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
                "From Messages, a browser or another app choose Share → Kenya Data Rights. KDR extracts identifiers and a classification locally.",
                color = KdrMuted,
            )
        }
    }
}

private fun feedbackText(label: LoanMessageLabel): String = when (label) {
    LoanMessageLabel.NON_LOAN -> "Not a loan"
    LoanMessageLabel.LOAN_MARKETING -> "Marketing"
    LoanMessageLabel.LOAN_APPLICATION -> "Application"
    LoanMessageLabel.LOAN_APPROVAL -> "Approval"
    LoanMessageLabel.LOAN_DISBURSEMENT -> "Disbursement"
    LoanMessageLabel.LOAN_REPAYMENT_REMINDER -> "Repayment"
    LoanMessageLabel.LOAN_OVERDUE_COLLECTION -> "Overdue / collection"
    LoanMessageLabel.CRB_NOTICE -> "CRB notice"
    LoanMessageLabel.LOAN_OTHER -> "Other loan"
}

@androidx.compose.runtime.Composable
private fun ObservationCard(
    observation: SharedObservation,
    allowFeedback: Boolean,
    feedbackLabel: LoanMessageLabel?,
    onFeedbackLabel: (LoanMessageLabel?) -> Unit,
) {
    Card(colors = CardDefaults.cardColors(containerColor = KdrPanel), shape = RoundedCornerShape(18.dp)) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text("Ephemeral analysis", fontWeight = FontWeight.Bold, fontSize = 20.sp)
            Text("Raw content retained: no", color = KdrGreen)
            if (observation.classifications.isNotEmpty()) {
                Text("Classifications", color = KdrMuted)
                val counts = observation.classifications.groupingBy { it.label.wireName }.eachCount()
                counts.entries.sortedByDescending { it.value }.forEach {
                    Text("${it.key}: ${it.value}", fontSize = 13.sp)
                }
            }

            if (allowFeedback) {
                val predicted = observation.classifications.single().label
                Text("Help tune the classifier", color = KdrCyan, fontWeight = FontWeight.Bold)
                Text(
                    "For this one explicitly shared message only, choose the correct class. The label is sent only if you later tap Send derived telemetry.",
                    color = KdrMuted,
                    fontSize = 13.sp,
                )
                FlowRow(
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    LoanMessageLabel.entries.forEach { label ->
                        Button(onClick = { onFeedbackLabel(if (feedbackLabel == label) null else label) }) {
                            val marker = if (feedbackLabel == label) "✓ " else ""
                            val predictedMarker = if (label == predicted) " (predicted)" else ""
                            Text("$marker${feedbackText(label)}$predictedMarker")
                        }
                    }
                }
            }

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
        }
    }
}

@androidx.compose.runtime.Composable
private fun TelemetryCard(
    serverUrl: String,
    pairingToken: String,
    status: String,
    uploading: Boolean,
    hasClassifications: Boolean,
    onServerUrlChange: (String) -> Unit,
    onPairingTokenChange: (String) -> Unit,
    onSave: () -> Unit,
    onClear: () -> Unit,
    onUpload: () -> Unit,
) {
    Card(colors = CardDefaults.cardColors(containerColor = KdrPanel), shape = RoundedCornerShape(18.dp)) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text("Your self-hosted learning server", fontWeight = FontWeight.Bold, fontSize = 20.sp)
            Text(
                "Pair with the HTTPS URL/token shown by the desktop installer. Pairing is encrypted with Android Keystore. Upload never happens automatically.",
                color = KdrMuted,
            )
            OutlinedTextField(
                value = serverUrl,
                onValueChange = onServerUrlChange,
                label = { Text("Server URL (HTTPS)") },
                singleLine = true,
            )
            OutlinedTextField(
                value = pairingToken,
                onValueChange = onPairingTokenChange,
                label = { Text("Pairing token") },
                singleLine = true,
                visualTransformation = PasswordVisualTransformation(),
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
            )
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(onClick = onSave) { Text("Save pairing") }
                Button(onClick = onClear) { Text("Clear") }
            }
            Button(onClick = onUpload, enabled = hasClassifications && !uploading) {
                Text(if (uploading) "Sending…" else "Send derived telemetry")
            }
            Text(status, color = KdrMuted, fontSize = 13.sp)
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
            Text("Android compatibility", fontWeight = FontWeight.Bold)
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("minSdk 23", color = KdrCyan)
                Spacer(Modifier.width(12.dp))
                Text("targetSdk 36", color = KdrMuted)
            }
            Text(
                if (scanAvailable) {
                    "Direct flavor · foreground communication scan + local classification"
                } else {
                    "Play flavor · permission-free share workflow + local classification"
                },
                color = KdrMuted,
            )
            Text(
                "API 26+ adds notification channels/adaptive icons; API 28+ can add BiometricPrompt without raising the API 23 baseline.",
                color = KdrMuted,
                fontSize = 13.sp,
            )
        }
    }
}
