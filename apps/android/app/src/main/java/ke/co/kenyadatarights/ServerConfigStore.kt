package ke.co.kenyadatarights

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

data class ServerConfig(val serverUrl: String, val token: String)

object ServerConfigStore {
    private const val alias = "kdr-mobile-server-v1"
    private const val prefsName = "kdr_secure_pairing"
    private const val ivKey = "config_iv"
    private const val cipherKey = "config_cipher"

    private fun secretKey(): SecretKey {
        val keyStore = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        val existing = keyStore.getKey(alias, null) as? SecretKey
        if (existing != null) return existing
        val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore")
        generator.init(
            KeyGenParameterSpec.Builder(
                alias,
                KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT,
            )
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setRandomizedEncryptionRequired(true)
                .build(),
        )
        return generator.generateKey()
    }

    fun save(context: Context, config: ServerConfig) {
        require(validateServerUrl(config.serverUrl)) { "Server URL must be HTTPS and contain no path/query" }
        require(config.token.length >= 32 && config.token.none(Char::isWhitespace)) { "Invalid pairing token" }
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, secretKey())
        val plaintext = "${config.serverUrl.trim()}\n${config.token}".toByteArray(Charsets.UTF_8)
        val encrypted = cipher.doFinal(plaintext)
        context.getSharedPreferences(prefsName, Context.MODE_PRIVATE).edit()
            .putString(ivKey, Base64.encodeToString(cipher.iv, Base64.NO_WRAP))
            .putString(cipherKey, Base64.encodeToString(encrypted, Base64.NO_WRAP))
            .apply()
    }

    fun load(context: Context): ServerConfig? = runCatching {
        val prefs = context.getSharedPreferences(prefsName, Context.MODE_PRIVATE)
        val iv = Base64.decode(prefs.getString(ivKey, null) ?: return null, Base64.NO_WRAP)
        val encrypted = Base64.decode(prefs.getString(cipherKey, null) ?: return null, Base64.NO_WRAP)
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE, secretKey(), GCMParameterSpec(128, iv))
        val parts = cipher.doFinal(encrypted).toString(Charsets.UTF_8).split("\n", limit = 2)
        if (parts.size != 2 || !validateServerUrl(parts[0])) return null
        ServerConfig(parts[0], parts[1])
    }.getOrNull()

    fun clear(context: Context) {
        context.getSharedPreferences(prefsName, Context.MODE_PRIVATE).edit().clear().apply()
    }
}
