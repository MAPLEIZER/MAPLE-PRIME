package ke.co.kenyadatarights

import android.Manifest
import android.content.Context
import android.net.Uri
import android.provider.CallLog

object CommunicationAccess {
    val requiredPermissions = arrayOf(Manifest.permission.READ_SMS, Manifest.permission.READ_CALL_LOG)
    const val available = true

    fun scan(context: Context, shouldContinue: () -> Boolean): SharedObservation {
        val phones = linkedSetOf<String>()
        val tokens = linkedSetOf<String>()
        val classifications = mutableListOf<MessageClassification>()
        val cutoff = System.currentTimeMillis() - ScanPolicy.lookbackDays * 24L * 60L * 60L * 1000L

        if (shouldContinue()) scanSms(context, cutoff, phones, tokens, classifications, shouldContinue)
        if (shouldContinue()) scanCalls(context, cutoff, phones, tokens, shouldContinue)

        return SharedObservation(
            phoneNumbers = phones.take(100).toSet(),
            tokens = tokens.take(100).toSet(),
            rawTextLength = 0,
            classifications = classifications.take(100),
        )
    }

    private fun scanSms(
        context: Context,
        cutoff: Long,
        phones: MutableSet<String>,
        tokens: MutableSet<String>,
        classifications: MutableList<MessageClassification>,
        shouldContinue: () -> Boolean,
    ) {
        val uri = Uri.parse("content://sms/inbox")
        val projection = arrayOf("address", "body", "date")
        context.contentResolver.query(uri, projection, "date >= ?", arrayOf(cutoff.toString()), "date DESC")?.use { cursor ->
            val addressIndex = cursor.getColumnIndex("address")
            val bodyIndex = cursor.getColumnIndex("body")
            var rows = 0
            while (shouldContinue() && cursor.moveToNext() && rows < ScanPolicy.maxSmsRows) {
                rows += 1
                val address = if (addressIndex >= 0) cursor.getString(addressIndex).orEmpty() else ""
                val body = if (bodyIndex >= 0) cursor.getString(bodyIndex).orEmpty() else ""
                merge(minimizeSharedObservation(address), phones, tokens)
                classifications.add(classifyMessage(body, sender = address))
                merge(minimizeSharedObservation(body), phones, tokens)
            }
        }
    }

    private fun scanCalls(
        context: Context,
        cutoff: Long,
        phones: MutableSet<String>,
        tokens: MutableSet<String>,
        shouldContinue: () -> Boolean,
    ) {
        val uri = CallLog.Calls.CONTENT_URI.buildUpon()
            .appendQueryParameter(CallLog.Calls.LIMIT_PARAM_KEY, ScanPolicy.maxCallRows.toString())
            .build()
        val projection = arrayOf(CallLog.Calls.NUMBER, CallLog.Calls.CACHED_NAME, CallLog.Calls.DATE)
        context.contentResolver.query(uri, projection, "${CallLog.Calls.DATE} >= ?", arrayOf(cutoff.toString()), "${CallLog.Calls.DATE} DESC")?.use { cursor ->
            val numberIndex = cursor.getColumnIndex(CallLog.Calls.NUMBER)
            val nameIndex = cursor.getColumnIndex(CallLog.Calls.CACHED_NAME)
            var rows = 0
            while (shouldContinue() && cursor.moveToNext() && rows < ScanPolicy.maxCallRows) {
                rows += 1
                val number = if (numberIndex >= 0) cursor.getString(numberIndex).orEmpty() else ""
                val name = if (nameIndex >= 0) cursor.getString(nameIndex).orEmpty() else ""
                merge(minimizeSharedObservation(number), phones, tokens)
                merge(minimizeSharedObservation(name), phones, tokens)
            }
        }
    }

    private fun merge(observation: SharedObservation, phones: MutableSet<String>, tokens: MutableSet<String>) {
        phones.addAll(observation.phoneNumbers)
        tokens.addAll(observation.tokens)
    }
}
