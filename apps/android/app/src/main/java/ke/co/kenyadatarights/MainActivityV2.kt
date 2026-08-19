package ke.co.kenyadatarights

import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.Lifecycle
import java.util.UUID

class MainActivityV2 : ComponentActivity() {
    private var section by mutableStateOf(defaultKdrSection())
    private var observation by mutableStateOf(SharedObservation(emptySet(), emptySet()))
    private var observationSource by mutableStateOf("manual")
    private var feedbackLabel by mutableStateOf<LoanMessageLabel?>(null)
    private var scanStatus by mutableStateOf("No device scan has run.")
    private var scanning by mutableStateOf(false)
    private var serverUrl by mutableStateOf("")
    private var pairingToken by mutableStateOf("")
    private var telemetryStatus by mutableStateOf("Server not paired.")
    private var uploading by mutableStateOf(false)
    private var testingServer by mutableStateOf(false)

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
            KdrV2Theme {
                KdrV2App(
                    selected = section,
                    onSelect = { section = it },
                    observation = observation,
                    scanAvailable = CommunicationAccess.available,
                    scanning = scanning,
                    scanStatus = scanStatus,
                    serverUrl = serverUrl,
                    pairingToken = pairingToken,
                    telemetryStatus = telemetryStatus,
                    uploading = uploading,
                    testingServer = testingServer,
                    feedbackLabel = feedbackLabel,
                    allowFeedback = observationSource == "shared_text" && observation.classifications.size == 1,
                    onFeedbackLabel = { feedbackLabel = it },
                    onServerUrlChange = { serverUrl = it.take(500) },
                    onPairingTokenChange = { pairingToken = it.take(200) },
                    onSavePairing = ::savePairing,
                    onClearPairing = ::clearPairing,
                    onTestServer = ::testServer,
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
        testingServer = false
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
            section = KdrSection.LEARN
        }
    }

    private fun requestForegroundScan() {
        section = KdrSection.SCAN
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
        if (config.token.length < 20) {
            telemetryStatus = "Pairing token looks incomplete."
            return
        }
        runCatching { ServerConfigStore.save(this, config) }
            .onSuccess { telemetryStatus = "Pairing saved with Android Keystore encryption. Test the connection next." }
            .onFailure { telemetryStatus = "Pairing could not be saved." }
    }

    private fun clearPairing() {
        ServerConfigStore.clear(this)
        pairingToken = ""
        serverUrl = ""
        telemetryStatus = "Pairing cleared."
    }

    private fun testServer() {
        if (!foregroundAccessAllowed || testingServer) return
        val config = ServerConfigStore.load(this)
        if (config == null) {
            telemetryStatus = "Save pairing first."
            return
        }
        testingServer = true
        telemetryStatus = "Testing authenticated mobile API…"
        Thread {
            val code = runCatching { TelemetryClient.status(config) }.getOrDefault(0)
            runOnUiThread {
                if (foregroundAccessAllowed) {
                    telemetryStatus = if (code in 200..299) {
                        "Connected. Authenticated mobile API is reachable over HTTPS."
                    } else {
                        "Connection test failed (HTTP $code). Check Tailscale/server URL and token."
                    }
                }
                testingServer = false
            }
        }.start()
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

private val V2Navy = Color(0xFF08111F)
private val V2Panel = Color(0xFF101D31)
private val V2PanelRaised = Color(0xFF162640)
private val V2Cyan = Color(0xFF67E8F9)
private val V2Green = Color(0xFF86EFAC)
private val V2Amber = Color(0xFFFDE68A)
private val V2Text = Color(0xFFE8F0FA)
private val V2Muted = Color(0xFF9FB0C5)

@Composable
private fun KdrV2Theme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = darkColorScheme(
            primary = V2Cyan,
            secondary = V2Green,
            background = V2Navy,
            surface = V2Panel,
            onBackground = V2Text,
            onSurface = V2Text,
        ),
        content = content,
    )
}

@Composable
private fun KdrV2App(
    selected: KdrSection,
    onSelect: (KdrSection) -> Unit,
    observation: SharedObservation,
    scanAvailable: Boolean,
    scanning: Boolean,
    scanStatus: String,
    serverUrl: String,
    pairingToken: String,
    telemetryStatus: String,
    uploading: Boolean,
    testingServer: Boolean,
    feedbackLabel: LoanMessageLabel?,
    allowFeedback: Boolean,
    onFeedbackLabel: (LoanMessageLabel?) -> Unit,
    onServerUrlChange: (String) -> Unit,
    onPairingTokenChange: (String) -> Unit,
    onSavePairing: () -> Unit,
    onClearPairing: () -> Unit,
    onTestServer: () -> Unit,
    onUpload: () -> Unit,
    onScan: () -> Unit,
) {
    Scaffold(
        containerColor = V2Navy,
        bottomBar = {
            NavigationBar(containerColor = V2Panel) {
                KdrSection.entries.forEach { item ->
                    NavigationBarItem(
                        selected = selected == item,
                        onClick = { onSelect(item) },
                        icon = { Text(navGlyph(item), fontSize = 16.sp) },
                        label = { Text(item.shortLabel, fontSize = 10.sp) },
                    )
                }
            }
        },
    ) { padding ->
        Surface(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding),
            color = V2Navy,
        ) {
            when (selected) {
                KdrSection.HOME -> HomeScreen(scanAvailable, serverUrl, observation, onSelect)
                KdrSection.SCAN -> ScanScreen(scanAvailable, scanning, scanStatus, observation, onScan)
                KdrSection.LEARN -> LearnScreen(observation, allowFeedback, feedbackLabel, onFeedbackLabel)
                KdrSection.SERVER -> ServerScreen(
                    serverUrl,
                    pairingToken,
                    telemetryStatus,
                    uploading,
                    testingServer,
                    observation.classifications.isNotEmpty(),
                    onServerUrlChange,
                    onPairingTokenChange,
                    onSavePairing,
                    onClearPairing,
                    onTestServer,
                    onUpload,
                )
                KdrSection.RIGHTS -> RightsScreen()
            }
        }
    }
}

private fun navGlyph(section: KdrSection): String = when (section) {
    KdrSection.HOME -> "⌂"
    KdrSection.SCAN -> "◎"
    KdrSection.LEARN -> "◆"
    KdrSection.SERVER -> "↕"
    KdrSection.RIGHTS -> "§"
}

@Composable
private fun ScreenColumn(title: String, subtitle: String, content: @Composable () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(V2Navy)
            .verticalScroll(rememberScrollState())
            .padding(18.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        Text(title, color = V2Cyan, fontWeight = FontWeight.Bold, fontSize = 26.sp)
        Text(subtitle, color = V2Muted, fontSize = 14.sp)
        content()
        Spacer(Modifier.height(10.dp))
    }
}

@Composable
private fun HomeScreen(
    scanAvailable: Boolean,
    serverUrl: String,
    observation: SharedObservation,
    onSelect: (KdrSection) -> Unit,
) {
    val flavor = if (scanAvailable) "Direct · foreground SMS/Call Log" else "Play · Share intake"
    ScreenColumn(
        "Kenya Data Rights",
        "KDR Android 0.2 alpha · ${BuildConfig.VERSION_NAME}",
    ) {
        HeroCard(
            "Privacy intelligence on your phone",
            "Classify loan-app communications locally, understand your data rights, and optionally contribute derived learning signals to your own KDR server.",
        )
        MetricCard("Build", flavor, V2Green)
        MetricCard("Server", if (serverUrl.isBlank()) "Not paired" else "Paired over HTTPS", if (serverUrl.isBlank()) V2Amber else V2Green)
        MetricCard("Ephemeral classifications", observation.classifications.size.toString(), V2Cyan)
        ActionCard(
            title = "Start here",
            actions = listOf(
                "Scan communications" to { onSelect(KdrSection.SCAN) },
                "Classifier & labels" to { onSelect(KdrSection.LEARN) },
                "Pair Mac/server" to { onSelect(KdrSection.SERVER) },
                "Know your rights" to { onSelect(KdrSection.RIGHTS) },
            ),
        )
        PrivacyBoundaryCard(scanAvailable)
    }
}

@Composable
private fun ScanScreen(
    scanAvailable: Boolean,
    scanning: Boolean,
    scanStatus: String,
    observation: SharedObservation,
    onScan: () -> Unit,
) {
    ScreenColumn("Scan", "Foreground-only communication analysis") {
        if (scanAvailable) {
            HeroCard(
                "Direct scan",
                "KDR reads a bounded recent window only after you press Scan. Processing stops when the app leaves the foreground.",
            )
            Button(onClick = onScan, enabled = !scanning, modifier = Modifier.fillMaxWidth()) {
                Text(if (scanning) "Scanning…" else "Scan recent SMS & calls")
            }
        } else {
            HeroCard(
                "Share intake",
                "This Play-compatible build does not request SMS or Call Log. In Messages, choose Share → Kenya Data Rights for one message.",
            )
        }
        StatusCard(scanStatus, if (scanning) V2Cyan else V2Muted)
        MetricCard("Phone identifiers", observation.phoneNumbers.size.toString(), V2Cyan)
        MetricCard("Candidate tokens", observation.tokens.size.toString(), V2Cyan)
        MetricCard("Classified messages", observation.classifications.size.toString(), V2Green)
        HeroCard(
            "Retention",
            "Raw SMS bodies and call rows are not written to KDR storage. Ephemeral scan results are cleared when the activity backgrounds.",
        )
    }
}

@Composable
private fun LearnScreen(
    observation: SharedObservation,
    allowFeedback: Boolean,
    feedbackLabel: LoanMessageLabel?,
    onFeedbackLabel: (LoanMessageLabel?) -> Unit,
) {
    ScreenColumn("Learn", "Loan-message classifier and human feedback") {
        if (observation.classifications.isEmpty()) {
            HeroCard(
                "No sample loaded",
                "Run a direct scan or explicitly Share one message into KDR. Classification happens locally before any optional telemetry step.",
            )
        } else {
            val counts = observation.classifications.groupingBy { it.label.wireName }.eachCount()
            HeroCard("Current model", "kdr-msg-v1 · lightweight deterministic baseline")
            counts.entries.sortedByDescending { it.value }.forEach { entry ->
                MetricCard(entry.key, entry.value.toString(), V2Green)
            }
        }
        if (allowFeedback) {
            Text("Correct this one shared message", color = V2Cyan, fontWeight = FontWeight.Bold, fontSize = 17.sp)
            Text(
                "A human label is attached only to this explicitly shared message, and is uploaded only if you later press Send derived telemetry on Server.",
                color = V2Muted,
                fontSize = 13.sp,
            )
            LoanMessageLabel.entries.forEach { label ->
                OutlinedButton(
                    onClick = { onFeedbackLabel(if (feedbackLabel == label) null else label) },
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    val prefix = if (feedbackLabel == label) "✓ " else ""
                    Text(prefix + label.wireName.replace('_', ' '))
                }
            }
        }
        HeroCard(
            "Training boundary",
            "Bulk scans remain unlabeled. The server may train stronger optional models only from explicit human labels, never by treating its own predictions as truth.",
        )
    }
}

@Composable
private fun ServerScreen(
    serverUrl: String,
    pairingToken: String,
    telemetryStatus: String,
    uploading: Boolean,
    testingServer: Boolean,
    hasTelemetry: Boolean,
    onServerUrlChange: (String) -> Unit,
    onPairingTokenChange: (String) -> Unit,
    onSavePairing: () -> Unit,
    onClearPairing: () -> Unit,
    onTestServer: () -> Unit,
    onUpload: () -> Unit,
) {
    ScreenColumn("Server", "Pair this phone to your self-hosted KDR instance") {
        HeroCard(
            "Mac / self-hosted pairing",
            "Use the HTTPS URL and token printed by the desktop installer's Pair Android option. The token is encrypted with Android Keystore on this phone.",
        )
        OutlinedTextField(
            value = serverUrl,
            onValueChange = onServerUrlChange,
            modifier = Modifier.fillMaxWidth(),
            label = { Text("HTTPS KDR server URL") },
            singleLine = true,
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri),
        )
        OutlinedTextField(
            value = pairingToken,
            onValueChange = onPairingTokenChange,
            modifier = Modifier.fillMaxWidth(),
            label = { Text("Pairing token") },
            singleLine = true,
            visualTransformation = PasswordVisualTransformation(),
        )
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button(onClick = onSavePairing, modifier = Modifier.weight(1f)) { Text("Save") }
            OutlinedButton(onClick = onTestServer, enabled = !testingServer, modifier = Modifier.weight(1f)) {
                Text(if (testingServer) "Testing…" else "Test")
            }
        }
        OutlinedButton(onClick = onClearPairing, modifier = Modifier.fillMaxWidth()) { Text("Clear pairing") }
        StatusCard(telemetryStatus, if (telemetryStatus.startsWith("Connected")) V2Green else V2Muted)
        Button(onClick = onUpload, enabled = hasTelemetry && !uploading, modifier = Modifier.fillMaxWidth()) {
            Text(if (uploading) "Sending derived features…" else "Send derived telemetry")
        }
        HeroCard(
            "Remote exposure",
            "The desktop installer publishes only /api/v1/mobile/ through Tailscale Serve. Dashboard and regulator actions remain local to the host.",
        )
    }
}

@Composable
private fun RightsScreen() {
    ScreenColumn("Rights", "Offline Kenya data-rights primer") {
        HeroCard(
            "Teaching mode",
            "These cards are educational guidance, not an automatic legal finding. The desktop KDR Legal Library provides searchable statutes, regulations and authoritative-source links.",
        )
        offlineRightsCards().forEach { right ->
            Card(
                colors = CardDefaults.cardColors(containerColor = V2Panel),
                shape = RoundedCornerShape(18.dp),
                modifier = Modifier.fillMaxWidth(),
            ) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(right.title, color = V2Cyan, fontWeight = FontWeight.Bold, fontSize = 17.sp)
                    Text(right.summary, color = V2Text, fontSize = 14.sp)
                    Text("Next: ${right.nextStep}", color = V2Muted, fontSize = 12.sp)
                }
            }
        }
        HeroCard(
            "Message triage",
            "A suspicious loan message can be evidence worth reviewing, but KDR does not automatically declare a data-protection breach from message content alone.",
        )
    }
}

@Composable
private fun HeroCard(title: String, body: String) {
    Card(
        colors = CardDefaults.cardColors(containerColor = V2Panel),
        shape = RoundedCornerShape(18.dp),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(title, color = V2Text, fontWeight = FontWeight.Bold, fontSize = 18.sp)
            Text(body, color = V2Muted, fontSize = 14.sp)
        }
    }
}

@Composable
private fun MetricCard(label: String, value: String, valueColor: Color) {
    Card(
        colors = CardDefaults.cardColors(containerColor = V2PanelRaised),
        shape = RoundedCornerShape(14.dp),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(14.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            Text(label, color = V2Muted, fontSize = 13.sp)
            Text(value, color = valueColor, fontWeight = FontWeight.Bold, fontSize = 13.sp)
        }
    }
}

@Composable
private fun StatusCard(text: String, color: Color) {
    Card(
        colors = CardDefaults.cardColors(containerColor = V2PanelRaised),
        shape = RoundedCornerShape(14.dp),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Text(text, color = color, modifier = Modifier.padding(14.dp), fontSize = 13.sp)
    }
}

@Composable
private fun ActionCard(title: String, actions: List<Pair<String, () -> Unit>>) {
    Card(
        colors = CardDefaults.cardColors(containerColor = V2Panel),
        shape = RoundedCornerShape(18.dp),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
            Text(title, color = V2Cyan, fontWeight = FontWeight.Bold, fontSize = 17.sp)
            actions.forEach { (label, action) ->
                OutlinedButton(onClick = action, modifier = Modifier.fillMaxWidth()) { Text(label) }
            }
        }
    }
}

@Composable
private fun PrivacyBoundaryCard(scanAvailable: Boolean) {
    HeroCard(
        "Privacy boundary",
        if (scanAvailable) {
            "Direct flavor: SMS and Call Log are queried only on an explicit foreground scan. No receiver or background scan service is used."
        } else {
            "Play flavor: no SMS or Call Log permission is declared. You explicitly Share one message into KDR."
        },
    )
}
