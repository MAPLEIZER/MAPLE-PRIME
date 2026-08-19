package ke.co.kenyadatarights

import java.net.HttpURLConnection
import java.net.URL

object TelemetryClient {
    fun status(config: ServerConfig): Int {
        require(validateServerUrl(config.serverUrl)) { "HTTPS server URL required" }
        val connection = URL(mobileStatusUrl(config)).openConnection() as HttpURLConnection
        try {
            connection.requestMethod = "GET"
            connection.connectTimeout = 8000
            connection.readTimeout = 8000
            connection.instanceFollowRedirects = false
            connection.setRequestProperty("Authorization", "Bearer ${config.token}")
            connection.setRequestProperty("Accept", "application/json")
            val code = connection.responseCode
            if (code !in 200..299) {
                connection.errorStream?.use { it.readBytes() }
            } else {
                connection.inputStream?.use { it.readBytes() }
            }
            return code
        } finally {
            connection.disconnect()
        }
    }

    fun submit(config: ServerConfig, event: TelemetryEvent): Int {
        require(validateServerUrl(config.serverUrl)) { "HTTPS server URL required" }
        val endpoint = URL(config.serverUrl.trimEnd('/') + "/api/v1/mobile/telemetry")
        val connection = endpoint.openConnection() as HttpURLConnection
        try {
            connection.requestMethod = "POST"
            connection.connectTimeout = 8000
            connection.readTimeout = 8000
            connection.doOutput = true
            connection.instanceFollowRedirects = false
            connection.setRequestProperty("Authorization", "Bearer ${config.token}")
            connection.setRequestProperty("Content-Type", "application/json; charset=utf-8")
            connection.setRequestProperty("Accept", "application/json")
            connection.outputStream.use { it.write(event.toJson().toByteArray(Charsets.UTF_8)) }
            val code = connection.responseCode
            if (code !in 200..299) {
                connection.errorStream?.use { it.readBytes() }
            } else {
                connection.inputStream?.use { it.readBytes() }
            }
            return code
        } finally {
            connection.disconnect()
        }
    }
}